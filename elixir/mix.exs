defmodule Numinous.MixProject do
  use Mix.Project

  def project do
    [
      app: :numinous,
      version: "0.2.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      description: "The ground the mesh floats in — right hemisphere to Manifold's left.",
      elixirc_paths: elixirc_paths(Mix.env()),
    ]
  end

  def application do
    [
      extra_applications: [:logger, :inets],
      mod: {Numinous.Application, []},
    ]
  end

  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:jason, "~> 1.4"},
      {:plug, "~> 1.15"},
      {:plug_cowboy, "~> 2.7"},
    ]
  end
end
