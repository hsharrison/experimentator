# Copyright (c) 2014 Henry S. Harrison
import itertools
import numpy as np

from experimentator.orderings import Shuffle


class Design():
    def __init__(self, ivs, design_matrix=None, ordering=None, **extra_context):
        self.ivs = ivs
        self.design_matrix = design_matrix
        self.extra_context = extra_context
        if ordering:
            self.ordering = ordering
        else:
            self.ordering = Shuffle()

        if not self.design_matrix and any(not iv_values for iv_values in self.ivs.values()):
            raise TypeError('Must specify a design matrix if using continuous IVs (values=None)')

        self.order = self.ordering.order

    def first_pass(self):
        if self.design_matrix:
            all_conditions = self._parse_design_matrix(self.design_matrix)
            for condition in all_conditions:
                condition.update(self.extra_context)

        else:
            all_conditions = self.full_cross(self.ivs)

        self.ordering.first_pass(all_conditions)

    @staticmethod
    def full_cross(ivs):
        try:
            iv_names, iv_values = zip(*ivs.items())
        except ValueError:
            # Workaround because zip doesn't want to return two elements if ivs is empty.
            iv_names = ()
            iv_values = ()
        iv_combinations = itertools.product(*iv_values)

        yield from (dict(zip(iv_names, iv_combination)) for iv_combination in iv_combinations)

    def _parse_design_matrix(self, design_matrix):
        if not np.shape(design_matrix)[1] == len(self.ivs):
            raise ValueError('Number of columns in design matrix not equal to number of IVs')

        values_per_factor = [np.unique(column) for column in np.transpose(design_matrix)]
        if any(iv_values and not len(iv_values) == len(values)
               for iv_values, values in zip(self.ivs.values(), values_per_factor)):
            raise ValueError('Unique elements in design matrix do not match number of values in IV definition')

        conditions = []
        for row in design_matrix:
            condition = self.extra_context.copy()
            for iv, factor_values, design_matrix_value in zip(self.ivs.items(), values_per_factor, row):
                if iv[1]:
                    condition.update({iv[0]: np.array(iv[1])[factor_values == design_matrix_value][0]})
                else:
                    condition.update({iv[0]: design_matrix_value})
            conditions.append(condition)

        return conditions


class DesignTree():
    def __init__(self, levels_and_designs):
        for level, level_above in zip(reversed(levels_and_designs[1:]), reversed(levels_and_designs[:-1])):
            new_ivs = level[1].first_pass()
            level_above.update(new_ivs)
            # And call first pass of the top level.
        levels_and_designs[0][1].first_pass()
        self.levels_and_designs = levels_and_designs

    def __next__(self):
        if len(self.levels_and_designs) == 1:
            raise StopIteration
        return DesignTree(self.levels_and_designs[1:])

    def __len__(self):
        return len(self.levels_and_designs)

    def __getitem__(self, item):
        return self.levels_and_designs[item]
