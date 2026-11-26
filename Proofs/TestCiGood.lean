import Mathlib

/-!
# Sum of the first n odd numbers

**Statement.** 1 + 3 + ⋯ + (2n − 1) = n².
**Proof sketch.** Induction on n: add 2n + 1 to n² to get (n + 1)².
-/

/-- `∑_{i<n} (2i+1) = n²`. -/
theorem sum_odd (n : ℕ) : ∑ i ∈ Finset.range n, (2 * i + 1) = n ^ 2 := by
  induction n with
  | zero => simp
  | succ n ih =>
    -- peel off the last term, use the induction hypothesis, then algebra
    rw [Finset.sum_range_succ, ih]
    ring

#print axioms sum_odd
