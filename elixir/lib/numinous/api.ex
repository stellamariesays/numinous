defmodule Numinous.Api do
  @moduledoc """
  REST API for the Numinous server.

  Endpoints:
    GET /              — server status
    GET /voids         — all active Voids (dark regions)
    GET /reach         — last reach scan results
    POST /scan         — force a new reach scan
    GET /pressure      — pressure map of all Voids
    GET /agents        — cached Manifold agents (from ManifoldClient)
    GET /health        — health check
  """

  use Plug.Router
  require Logger

  plug :match
  plug :dispatch

  get "/" do
    send_json(conn, %{
      name: "numinous",
      description: "The ground the mesh floats in",
      status: "running",
      void_count: length(Numinous.Field.list_voids()),
      manifold_url: Application.get_env(:numinous, :manifold_url),
    })
  end

  get "/health" do
    send_json(conn, %{status: "ok"})
  end

  get "/voids" do
    voids = Numinous.Field.list_voids()
    send_json(conn, %{voids: voids, count: length(voids)})
  end

  get "/pressure" do
    pressure = Numinous.Field.pressure_map()
    send_json(conn, %{pressure: pressure})
  end

  get "/reach" do
    case Numinous.Scout.get_last_scan() do
      nil -> send_json(conn, %{status: "no_scan_yet"}, 404)
      scan -> send_json(conn, scan)
    end
  end

  post "/scan" do
    Logger.info("api: forcing reach scan")
    Numinous.Scout.force_scan()
    scan = Numinous.Scout.get_last_scan()
    send_json(conn, scan || %{status: "scan_failed"})
  end

  get "/agents" do
    agents = Numinous.ManifoldClient.get_agents()
    send_json(conn, %{agents: agents, count: length(agents)})
  end

  match _ do
    send_json(conn, %{error: "not_found"}, 404)
  end

  # ── Helpers ──

  defp send_json(conn, data, status \\ 200) do
    conn
    |> Plug.Conn.put_resp_content_type("application/json")
    |> Plug.Conn.send_resp(status, Jason.encode!(data))
  end
end

defmodule Numinous.ApiSupervisor do
  use Supervisor

  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    port = Application.get_env(:numinous, :port, 8780)

    children = [
      {Plug.Cowboy, scheme: :http, plug: Numinous.Api, options: [port: port]},
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end
end
