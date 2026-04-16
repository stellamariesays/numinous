defmodule Numinous.ManifoldClient do
  @moduledoc """
  HTTP client for the Manifold federation REST API.

  Reads the live mesh state (agents, capabilities) so Numinous can run
  reach scans without being part of the mesh itself.
  """

  use GenServer
  require Logger

  @refresh_interval 60_000

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def get_agents do
    GenServer.call(__MODULE__, :get_agents)
  end

  def get_capabilities do
    GenServer.call(__MODULE__, :get_capabilities)
  end

  # ── GenServer ──

  @impl true
  def init(_opts) do
    state = %{agents: [], capabilities: [], manifold_url: manifold_url()}
    send(self(), :refresh)
    {:ok, state}
  end

  @impl true
  def handle_call(:get_agents, _from, state) do
    {:reply, state.agents, state}
  end

  @impl true
  def handle_call(:get_capabilities, _from, state) do
    {:reply, state.capabilities, state}
  end

  @impl true
  def handle_info(:refresh, state) do
    state = refresh(state)
    Process.send_after(self(), :refresh, @refresh_interval)
    {:noreply, state}
  end

  # ── Internal ──

  defp refresh(state) do
    url = state.manifold_url

    with {:ok, agents_body} <- http_get("#{url}/agents"),
         {:ok, decoded} <- Jason.decode(agents_body) do
      agents = Map.get(decoded, "agents", [])
      caps = agents
        |> Enum.flat_map(&Map.get(&1, "capabilities", []))
        |> Enum.uniq()

      Logger.info("manifold client: refreshed #{length(agents)} agents, #{length(caps)} capabilities")
      %{state | agents: agents, capabilities: caps}
    else
      {:error, reason} ->
        Logger.warning("manifold client: refresh failed — #{inspect(reason)}")
        state
    end
  end

  defp http_get(url) do
    case :httpc.request(:get, {String.to_charlist(url), []}, [{:timeout, 5000}], []) do
      {:ok, {{_status, 200, _}, _headers, body}} -> {:ok, to_string(body)}
      {:ok, {{_status, code, _}, _, body}} -> {:error, {code, to_string(body)}}
      {:error, reason} -> {:error, reason}
    end
  end

  defp manifold_url do
    Application.get_env(:numinous, :manifold_url, "http://localhost:8777")
  end
end
