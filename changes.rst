Changes
=======

0.2.4 (07/31/2014)
------------------

- Add |ExperimentSection.description| property.
- Reduce number of debug messages when running sections.
- Fix bug where parent sections would be marked as having started after running demo trials.
- Workaround for pandas bug (issue 7380) where comparing two different DataFrames would raise an exception instead of returning ``False``.
- Comparing any of experimentator's objects to a different type now returns ``False``.

0.2.3 (07/21/2014)
------------------

- Allow tuple indexing.

0.2.2 (07/03/2014)
------------------

- Report coverage to coveralls.
- Add contact request to README.
- Make badges prettier.

0.2.1 (07/01/2014)
------------------

- Minor documentation improvements.


.. |ExperimentSection.description| replace:: :attr:`ExperimentSection.property <experimentator.ExperimentSection.description>`
