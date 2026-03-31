defmodule Numinous.MixProject do
  use Mix.Project

  def project do
    [
      app: :numinous,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      description: "The ground the mesh floats in — right hemisphere to Manifold's left.",
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {Numinous.Application, []},
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"},
    ]
  end
end
