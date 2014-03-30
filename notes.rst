Notes
=====

Heterogeneous DesignTree constructor?
-------------------------------------

Associate tree structure with an IV at a particular level.
This could be accomplished with either a hard-coded IV name (e.g. ``'structure'``),
or identified by keyword argument (e.g. ``structure_iv='structure'``).
The former is more readable, I think.
In any case, values of this IV correspond to named ``DesignTree`` instances
and therefore heterogeneous paths down the tree.

Questions:
- How should ``next(tree)`` work?
  Return multiple ``DesignTree`` children.
  Handle it in the ``ExperimentSection`` constructor.
- How should non-atomic sorts work?
  The automatically-created IVs of different ``DesignTree`` instances will collide.
