import Config

config :numinous,
  manifold_url: System.get_env("MANIFOLD_URL", "http://localhost:8777"),
  scan_interval_ms: String.to_integer(System.get_env("SCAN_INTERVAL_MS", "1800000")),
  max_voids: String.to_integer(System.get_env("MAX_VOIDS", "10")),
  port: String.to_integer(System.get_env("NUMINOUS_PORT", "8780")),
  python_path: System.get_env("PYTHON_PATH", "/home/sophia/venv/bin/python3"),
  # Path to numinous Python package (for reach_scan)
  numinous_python: System.get_env("NUMINOUS_PYTHON", "/home/sophia/numinous"),
  manifold_python: System.get_env("MANIFOLD_PYTHON", "/home/sophia/Manifold")

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]
