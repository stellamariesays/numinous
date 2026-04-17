defmodule Numinous.Memory do
  @moduledoc """
  Memory persists Void state to disk as .md files.

  Subscribes to the VoidRegistry and renders focus files that match
  the fog state. The Python side (dynamics/session.py) symlinks or
  reads from the output directory.

  ## Output structure

      memory_output/
      ├── void-state.md          # All active dark circles + pressure
      ├── terrain-delta.md       # What changed since last render
      └── focus/                 # Per-void files
          └── <term>.md          # Individual void state

  ## Wiring

  Add to application supervision tree (before Scout, after Field):

      {Numinous.Memory, output_dir: "/home/sophia/numinous/memory/output"}

  """

  use GenServer
  require Logger

  @default_output "/home/sophia/numinous/memory/output"
  @render_interval_ms 15_000

  # ── Public API ───────────────────────────────────────────────────────────────

  def start_link(opts \\ []) do
    output_dir = Keyword.get(opts, :output_dir, @default_output)
    GenServer.start_link(__MODULE__, %{output_dir: output_dir}, name: __MODULE__)
  end

  @doc "Force a render cycle now."
  def render do
    GenServer.call(__MODULE__, :render)
  end

  @doc "Get the output directory path."
  def output_dir do
    GenServer.call(__MODULE__, :output_dir)
  end

  # ── GenServer callbacks ──────────────────────────────────────────────────────

  @impl true
  def init(state) do
    output_dir = state.output_dir

    # Ensure output directories exist
    File.mkdir_p!(output_dir)
    File.mkdir_p!(Path.join(output_dir, "focus"))

    Logger.info("memory: output dir #{output_dir}")

    # Snapshot the initial state
    prev = snapshot_voids()

    schedule_render()

    {:ok, Map.merge(state, %{
      prev_snapshot: prev,
      render_count: 0,
    })}
  end

  @impl true
  def handle_call(:render, _from, state) do
    state = do_render(state)
    {:reply, :ok, state}
  end

  @impl true
  def handle_call(:output_dir, _from, state) do
    {:reply, state.output_dir, state}
  end

  @impl true
  def handle_info(:render_tick, state) do
    state = do_render(state)
    schedule_render()
    {:noreply, state}
  end

  # ── Internal ─────────────────────────────────────────────────────────────────

  defp schedule_render do
    Process.send_after(self(), :render_tick, @render_interval_ms)
  end

  defp do_render(state) do
    current = snapshot_voids()
    ts = timestamp()

    # Write void-state.md
    write_void_state(state.output_dir, current, ts)

    # Write terrain-delta.md if something changed
    write_terrain_delta(state.output_dir, state.prev_snapshot, current, ts)

    # Write per-void focus files
    write_focus_files(state.output_dir, current, ts)

    %{state | prev_snapshot: current, render_count: state.render_count + 1}
  end

  defp snapshot_voids do
    Numinous.Field.list_voids()
  end

  defp write_void_state(output_dir, voids, ts) do
    header = ["# Void State", "*Rendered: #{ts}*", ""]

    body = if voids == [] do
      ["No active dark circles.", ""]
    else
      ["## Active Voids (#{length(voids)})", ""] ++
      Enum.map(voids, fn v ->
        bar = pressure_bar(v.pressure)
        implied = Enum.join(v.implied_by, ", ")
        age_s = div(Map.get(v, :age_ms, 0), 1000)
        "- **#{v.term}** #{bar} pressure=#{Float.round(v.pressure, 3)} age=#{age_s}s implied_by: #{implied}"
      end) ++ [""]
    end

    max_pressure = voids |> Enum.map(& &1.pressure) |> Enum.max(fn -> 0.0 end)
    warning = if max_pressure > 0.8 do
      ["⚠️ **HIGH PRESSURE** detected — max #{Float.round(max_pressure, 3)}", ""]
    else
      []
    end

    File.write!(Path.join(output_dir, "void-state.md"), Enum.join(header ++ body ++ warning, "\n"))
  end

  defp write_terrain_delta(output_dir, prev, current, ts) do
    prev_map = Map.new(prev, & {&1.term, &1})
    curr_map = Map.new(current, & {&1.term, &1})

    all_terms = MapSet.union(MapSet.new(Map.keys(prev_map)), MapSet.new(Map.keys(curr_map)))

    {deltas, _} = Enum.reduce(all_terms, {[], false}, fn term, {lines, changed} ->
      prev_v = Map.get(prev_map, term)
      curr_v = Map.get(curr_map, term)

      cond do
        # New void appeared
        prev_v == nil and curr_v != nil ->
          {lines ++ ["+ **#{term}** opened — pressure #{Float.round(curr_v.pressure, 3)}"], true}

        # Void disappeared (named or died)
        curr_v == nil and prev_v != nil ->
          {lines ++ ["- **#{term}** closed (was #{Float.round(prev_v.pressure, 3)})"], true}

        # Pressure shifted > 0.1
        prev_v != nil and curr_v != nil ->
          delta = abs(curr_v.pressure - prev_v.pressure)
          if delta > 0.1 do
            {lines ++ ["~ **#{term}** pressure #{Float.round(prev_v.pressure, 3)} → #{Float.round(curr_v.pressure, 3)}"], true}
          else
            {lines, changed}
          end

        true ->
          {lines, changed}
      end
    end)

    if deltas != [] do
      content = [
        "# Terrain Delta",
        "*Rendered: #{ts}*",
        "",
        "## Changes",
        "",
      ] ++ deltas ++ [""]

      File.write!(Path.join(output_dir, "terrain-delta.md"), Enum.join(content, "\n"))
    end
    # If nothing changed, don't overwrite the previous delta
  end

  defp write_focus_files(output_dir, voids, ts) do
    focus_dir = Path.join(output_dir, "focus")

    # Clear stale focus files for voids that no longer exist
    existing = File.ls!(focus_dir) |> Enum.filter(&String.ends_with?(&1, ".md"))
    current_terms = MapSet.new(voids, & &1.term)

    Enum.each(existing, fn fname ->
      term = String.replace_suffix(fname, ".md", "")
      unless MapSet.member?(current_terms, term) do
        File.rm(Path.join(focus_dir, fname))
      end
    end)

    # Write current voids
    Enum.each(voids, fn v ->
      content = [
        "# Focus: #{v.term}",
        "*Rendered: #{ts}*",
        "",
        "pressure: #{Float.round(v.pressure, 3)}",
        "age: #{div(Map.get(v, :age_ms, 0), 1000)}s",
        "implied_by: #{Enum.join(v.implied_by, ", ")}",
        "",
      ]
      safe_name = v.term |> String.replace(~r/[^\w\-]/, "_")
      File.write!(Path.join(focus_dir, "#{safe_name}.md"), Enum.join(content, "\n"))
    end)
  end

  defp pressure_bar(p) when p >= 0.8, do: "🔴"
  defp pressure_bar(p) when p >= 0.5, do: "🟡"
  defp pressure_bar(_), do: "🟢"

  defp timestamp do
    DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M UTC")
  end
end
