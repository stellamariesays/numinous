defmodule Numinous.Scout do
  @moduledoc """
  The Scout periodically runs reach scans and opens Voids for the top results.

  It watches the mesh from outside — never joining, never participating.
  When it finds dark regions, it opens Void processes in the Field.
  When a region gets covered by a new agent, the Void gets named and exits.

  The Scout is the heartbeat of the right hemisphere.
  """

  use GenServer
  require Logger

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def force_scan do
    GenServer.call(__MODULE__, :force_scan, 60_000)
  end

  def get_last_scan do
    GenServer.call(__MODULE__, :get_last_scan)
  end

  # ── GenServer ──

  @impl true
  def init(_opts) do
    interval = Application.get_env(:numinous, :scan_interval_ms, 1_800_000)
    state = %{interval: interval, last_scan: nil, timer: nil}
    # First scan async — don't block startup
    send(self(), :scan)
    {:ok, state}
  end

  @impl true
  def handle_call(:force_scan, _from, state) do
    {:reply, :ok, do_scan(state)}
  end

  @impl true
  def handle_call(:get_last_scan, _from, state) do
    {:reply, state.last_scan, state}
  end

  @impl true
  def handle_info(:scan, state) do
    new_state = state |> do_scan() |> schedule_scan()
    {:noreply, new_state}
  end

  # ── Internal ──

  defp schedule_scan(state) do
    timer = Process.send_after(self(), :scan, state.interval)
    %{state | timer: timer}
  end

  defp do_scan(state) do
    Logger.info("scout: running reach scan")

    case Numinous.ReachBridge.run_scan(top_n: 20) do
      {:ok, result} ->
        regions = Map.get(result, "regions", [])
        max_voids = Application.get_env(:numinous, :max_voids, 10)

        # Get existing void terms to avoid re-opening
        existing = Numinous.Field.list_voids() |> Enum.map(& &1.term)

        # Close voids that are no longer in the scan results
        close_stale_voids(regions, existing)

        # Open new voids for top regions
        regions
        |> Enum.reject(fn r -> r["term"] in existing end)
        |> Enum.take(max(0, max_voids - length(existing)))
        |> Enum.each(fn r ->
          {:ok, _pid} = Numinous.Field.open_void(
            r["term"],
            r["implied_by"],
            r["strength"]
          )
        end)

        %{state | last_scan: result}

      {:error, reason} ->
        Logger.error("scout: scan failed — #{inspect(reason)}")
        state
    end
  end

  defp close_stale_voids(current_regions, existing_voids) do
    current_terms = MapSet.new(current_regions, & &1["term"])

    Enum.each(existing_voids, fn term ->
      if not MapSet.member?(current_terms, term) do
        case Registry.lookup(Numinous.VoidRegistry, term) do
          [{pid, _}] -> Numinous.Void.name(pid, "scout-expiry")
          [] -> :ok
        end
      end
    end)
  end
end
