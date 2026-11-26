import Mathlib

/-! # Smoke test for the Lean 4 + Mathlib setup -/

/-- Kernel computation: `1 + 1 = 2` on natural numbers. -/
theorem one_add_one : (1 : ℕ) + 1 = 2 := rfl

/-- The sum of two even integers is even. -/
theorem even_add_even (a b : ℤ) (ha : Even a) (hb : Even b) : Even (a + b) := by
  obtain ⟨k, rfl⟩ := ha
  obtain ⟨m, rfl⟩ := hb
  exact ⟨k + m, by ring⟩

/-- A Mathlib-dependent fact: `√2` is irrational. -/
theorem sqrt_two_irrational : Irrational (Real.sqrt 2) := by
  simpa using Nat.Prime.irrational_sqrt Nat.prime_two

-- Prints the axioms used; must NOT list `sorryAx`.
#print axioms even_add_even
#print axioms sqrt_two_irrational
