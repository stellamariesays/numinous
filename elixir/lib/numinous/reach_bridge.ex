defmodule Numinous.ReachBridge do
  @moduledoc """
  Python bridge for reach_scan.

  Calls the numinous Python package's reach_scan() against the current
  Manifold atlas data. Returns structured reach results to the Elixir runtime.

  The bridge uses a Python subprocess to avoid embedding a Python interpreter.
  Each scan spawns a fresh process — no state leaks between runs.
  """

  require Logger

  @doc """
  Run a reach scan against the current Manifold atlas.

  Returns {:ok, %ReachReading{}} with candidate regions, or {:error, reason}.

  The Python script reads agent data from the Manifold REST API directly,
  builds a CapabilityRegistry + Atlas, runs reach_scan, and prints JSON.
  """
  def run_scan(opts \\ []) do
    top_n = Keyword.get(opts, :top_n, 15)
    python = Application.get_env(:numinous, :python_path, "python3")
    numinous_path = Application.get_env(:numinous, :numinous_python)
    manifold_path = Application.get_env(:numinous, :manifold_python)
    manifold_url = Application.get_env(:numinous, :manifold_url, "http://localhost:8777")

    python_code = """
import json, sys, urllib.request
sys.path.insert(0, '#{manifold_path}')
sys.path.insert(0, '#{numinous_path}')

from core import Atlas
from core.registry import CapabilityRegistry
from numinous.reach import reach_scan

agents_raw = json.loads(urllib.request.urlopen('#{manifold_url}/agents', timeout=10).read())
reg = CapabilityRegistry()
for a in agents_raw['agents']:
    reg.update_from_announcement({'name': a['name'], 'capabilities': a.get('capabilities', [])})

atlas = Atlas.build(reg)
reading = reach_scan(atlas, top_n=#{top_n})

result = {
    'interpretation': reading.interpretation,
    'total_implied': reading.total_implied,
    'regions': [
        {
            'term': r.term,
            'strength': r.strength,
            'implied_by': r.implied_by[:5],
            'covering_agents': r.covering_agents,
            'interpretation': r.interpretation,
        }
        for r in reading.candidate_regions
    ],
    'seam_hints': reading.seam_hints,
}
print(json.dumps(result))
"""

    args = ["-c", python_code]

    case System.cmd(python, args, stderr_to_stdout: false) do
      {output, 0} ->
        case Jason.decode(output) do
          {:ok, result} ->
            Logger.info("reach bridge: scan complete — #{length(result["regions"])} regions, #{result["total_implied"]} total implied")
            {:ok, result}
          {:error, reason} ->
            Logger.error("reach bridge: JSON decode failed — #{inspect(reason)}")
            {:error, {:decode_error, reason}}
        end

      {stderr, code} ->
        Logger.error("reach bridge: Python exited #{code} — #{stderr}")
        {:error, {:python_error, code, stderr}}
    end
  rescue
    e -> {:error, {:exception, Exception.message(e)}}
  end
end
