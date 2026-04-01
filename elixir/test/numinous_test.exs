defmodule NuminousTest do
  use ExUnit.Case, async: false

  setup do
    # Each test gets a clean Field — stop any running voids first
    Numinous.voids()
    |> Enum.each(fn v -> Numinous.name(v.term, "test-cleanup") end)
    :ok
  end

  test "from_holes caps at 5 voids" do
    holes = Enum.map(1..10, fn i ->
      %{"term" => "void-#{i}", "implied_by" => [], "pressure" => i / 10}
    end)

    Numinous.open(holes)
    assert length(Numinous.voids()) == 5
  end

  test "voids are sorted by pressure descending" do
    Numinous.open([
      %{"term" => "low",  "pressure" => 0.1},
      %{"term" => "high", "pressure" => 0.9},
      %{"term" => "mid",  "pressure" => 0.5},
    ])

    [first | _] = Numinous.voids()
    assert first.term == "high"
  end

  test "name_void removes the void from the field" do
    Numinous.open([%{"term" => "agent-identity", "pressure" => 0.4}])
    assert Enum.any?(Numinous.voids(), &(&1.term == "agent-identity"))

    Numinous.name("agent-identity", "stella")
    Process.sleep(50)
    refute Enum.any?(Numinous.voids(), &(&1.term == "agent-identity"))
  end

  test "name_void on unknown term returns error" do
    assert {:error, :not_found} = Numinous.name("does-not-exist", "stella")
  end

  test "pressure_map returns term => pressure map" do
    Numinous.open([
      %{"term" => "solar-memory", "pressure" => 0.3},
      %{"term" => "deploy-model", "pressure" => 0.5},
    ])

    map = Numinous.pressure_map()
    assert map["solar-memory"] == 0.3
    assert map["deploy-model"] == 0.5
  end
end
