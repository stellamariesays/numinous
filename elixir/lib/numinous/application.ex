defmodule Numinous.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Void registry — names for Void processes
      {Registry, keys: :unique, name: Numinous.VoidRegistry},

      # DynamicSupervisor for Void processes
      Numinous.Field,

      # REST API — start early so port is available
      Numinous.ApiSupervisor,

      # Manifold federation client (caches agent/capability data)
      Numinous.ManifoldClient,

      # Scout — periodic reach scanner (starts last, may block on Python)
      Numinous.Scout,
    ]

    opts = [strategy: :one_for_one, name: Numinous.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
