"""Experimentator API module.

This module contains shortcuts that help to create common experimental designs.

"""
from experimentator.design import Design, DesignTree
from experimentator.experiment import Experiment
from experimentator.order import Shuffle


def within_subjects_experiment(ivs, n_participants, design_matrix=None, ordering=None, experiment_file=None):
    """Construct a within-subjects experiment.

    This function creates a within-subjects experiment, in which all the IVs are at the trial level.

    Arguments
    ---------
    ivs : list or dict
        A list of the experiment's IVs, specified in the form of tuples with the first element being the
        IV name and the second element a list of its possible values. Alternatively, the IVs at each level can be
        specified in a dictionary. See documentation for `Design` for more information on specifying IVs.
    n_participants : int
        Number of participants to initialize.
    design_matrix : array-like, optional
        Design matrix for the experiment. If not specified, IVs will be fully crossed. See documentation for `Design`
        for more on design matrices.
    ordering : Ordering, optional
        An instance of the class `Ordering` or one of its descendants, specifying how the trials will be ordered. If not
        specified, `Shuffle` will be used.
    experiment_file : str, optional
        File location to save the experiment.

    Returns
    -------
    Experiment
        The constructed experiment.

    """
    levels_and_designs = [('participant', Design(ordering=Shuffle(n_participants))),
                          ('trial', Design(ivs=ivs, design=design_matrix, ordering=ordering))]

    experiment = Experiment(DesignTree(levels_and_designs), experiment_file=experiment_file)

    if experiment_file:
        experiment.save()

    return experiment


def blocked_experiment(trial_ivs, n_participants,
                       design_matrices=None,
                       orderings=None,
                       block_ivs=None,
                       experiment_file=None):
    """Construct a within-subjects experiment.

    This function creates a blocked within-subjects experiment, in which all the IVs are at either the trial level or
    the block level.

    Arguments
    ---------
    trial_ivs : list or dict
        A list of the IVs to define at the trial level, specified in the form of tuples with the first element being the
        IV name and the second element a list of its possible values. Alternatively, the IVs at each level can be
        specified in a dictionary. See documentation for `Design` for more information on specifying IVs.
    n_participants : int
        Number of participants to initialize.
    design_matrices : dict, optional
        Design matrices for the experiment. Keys are ``'trial'`` and ``'block'``; values are the respective design
        matrices (if any). If not specified, IVs will be fully crossed. See documentation for `Design` for more on
        design matrices.
    orderings : dict, optional
        Dictionary with keys of ``'trial'`` and ``'block'``. Each value should be an instance of the class `Ordering` or
        one of its descendants, specifying how the trials will be ordered. If not specified, `Shuffle` will be used.
    block_ivs : list or dict, optional
        IVs to define at the block level. See documentation for `Design` for more information on specifying IVs.
    experiment_file : str, optional
        File location to save the experiment.

    Note
    ----
    For blocks to have any effect, you should either define at least one IV at the block level (for non-identical
    blocks), or use the ordering ``Ordering(n)`` to create ``n`` identical blocks for every participant (Identical in
    the design sense; the order of trials will depend on the trial ordering and will probably not be identical between
    blocks).

    Returns
    -------
    Experiment
        The constructed experiment.

    """
    if not design_matrices:
        design_matrices = {}
    if not orderings:
        orderings = {}

    levels_and_designs = [('participant', Design(ordering=Shuffle(n_participants)),
                           ('block', Design(ivs=block_ivs,
                                            design=design_matrices.get('block'),
                                            ordering=orderings.get('trial')),
                            ('trial', Design(ivs=trial_ivs,
                                             design=design_matrices.get('trial'),
                                             ordering=orderings.get('trial')))))]

    experiment = Experiment(DesignTree(levels_and_designs))

    if experiment_file:
        experiment.save()

    return experiment


def standard_experiment(levels, ivs_by_level,
                        design_matrices_by_level=None,
                        ordering_by_level=None,
                        experiment_file=None):
    """Construct a standard experiment.

    This function builds a standard experiment, which is to say an experiment that has arbitrary levels but only one
    design at each level, and the same structure everywhere in the hierarchy.

    Arguments
    ---------
    levels : sequence of str
        Names of the levels of the experiment
    ivs_by_level : dict
        Dictionary specifying the IVs and their possible values at every level. The keys are be the level names, and the
        values are lists of the IVs at that level, specified in the form of tuples with the first element being the IV
        name and the second element a list of its possible values. Alternatively, the IVs at each level can be
        specified in a dictionary. See documentation for `Design` for more information on specifying IVs.
    design_matrices_by_level : dict, optional
        Specify the design matrix for any levels. Keys are level names; values are design matrices. Any levels without
        a design matrix will be fully crossed. See `Design` for more on design matrices.
    ordering_by_level : dict, optional
        Specify the ordering for each level. Keys are level names; values are instance objects from
        `experimentator.order`. For ny levels without an order specified, `Shuffle` will be used.
    experiment_file : str, optional
        File location to save the experiment.

    Returns
    -------
    Experiment
        The constructed experiment.

    """
    if not design_matrices_by_level:
        design_matrices_by_level = {}
    if not ordering_by_level:
        ordering_by_level = {}

    levels_and_designs = [(level, [Design(ivs=ivs_by_level.get(level),
                                   design_matrix=design_matrices_by_level.get(level),
                                   ordering=ordering_by_level.get(level))])
                          for level in levels]

    experiment = Experiment(DesignTree(levels_and_designs), experiment_file=experiment_file)

    if experiment_file:
        experiment.save()

    return experiment
