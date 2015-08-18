from collections import Counter
from datetime import datetime
import numpy as np
import pandas as pd


class OneHotFeaturizer(object):
    """
    One-hot encoder for a categorical feature.

    Behaves like a composition of sklearn's LabelEncoder (with support for an
    "other" label) and OneHotEncoder.
    """
    def __init__(self, col_name, min_seen_count=10):
        self.col_name = col_name
        self._counter = None
        self.val_to_int = None
        self.int_to_val = None
        self.min_seen_count = min_seen_count

    def fit(self, dataset):
        """
        Build the featurizer using the given dataset (DataFrame).
        """
        # Build a map from string feature values to unique integers.
        # Assumes 'other' does not occur as a value.
        self.val_to_int = {'other': 0}
        self.int_to_val = ['other']
        next_index = 1
        self._counter = Counter(dataset[self.col_name])
        for val, count in self._counter.iteritems():
            assert val not in self.val_to_int
            if count >= self.min_seen_count:
                self.val_to_int[val] = next_index
                self.int_to_val.append(val)
                next_index += 1
        assert len(self.val_to_int) == next_index
        assert len(self.int_to_val) == next_index

    def transform(self, dataset):
        """
        Featurize the given dataset (DataFrame) and return result as DataFrame.
        """
        feats = np.zeros(
            (len(dataset), len(self.val_to_int)), dtype=bool)
        for i, val in enumerate(dataset[self.col_name]):
            if val in self.val_to_int:
                feats[i][self.val_to_int[val]] = True
            else:
                feats[i][self.val_to_int['other']] = True
        feat_names = [
            '{} {}'.format(self.col_name, val)
            for val in self.int_to_val]
        return pd.DataFrame(
            feats, index=dataset.index, columns=feat_names)


class ListFeaturizer(object):
    """
    Binary featurizer for a feature that takes list-of-strings values.
    """
    # FIXME: This is very similar to OneHotFeaturizer; make DRY.

    def __init__(self, col_name, min_seen_count=10):
        self.col_name = col_name
        self._counter = None
        self.val_to_int = None
        self.int_to_val = None
        self.min_seen_count = min_seen_count

    def fit(self, dataset):
        """
        Build the featurizer using the given dataset (DataFrame).
        """
        # Build a map from string feature values to unique integers.
        # Assumes 'other' does not occur as a value.
        self.val_to_int = {'other': 0}
        self.int_to_val = ['other']
        next_index = 1
        self._counter = Counter()
        for list_of_vals in dataset[self.col_name]:
            self._counter.update(list_of_vals)
        for val, count in self._counter.iteritems():
            assert val not in self.val_to_int
            if count >= self.min_seen_count:
                self.val_to_int[val] = next_index
                self.int_to_val.append(val)
                next_index += 1
        assert len(self.val_to_int) == next_index
        assert len(self.int_to_val) == next_index

    def transform(self, dataset):
        """
        Featurize the given dataset (DataFrame) and return result as DataFrame.
        """
        feats = np.zeros(
            (len(dataset), len(self.val_to_int)), dtype=bool)
        for i, list_of_vals in enumerate(dataset[self.col_name]):
            for val in list_of_vals:
                if val in self.val_to_int:
                    feats[i][self.val_to_int[val]] = True
                else:
                    feats[i][self.val_to_int['other']] = True
        feat_names = [
            '{} {}'.format(self.col_name, val)
            for val in self.int_to_val]
        return pd.DataFrame(
            feats, index=dataset.index, columns=feat_names)


class CountListFeaturizer(object):
    """
    Featurizer for features that are lists of (str, count) tuples.

    Each str become its own real-valued feature, with the count as the value of
    that feature.
    """
    # FIXME: This is very similar to OneHotFeaturizer; make DRY.

    def __init__(self, col_name, min_seen_count=10):
        self.col_name = col_name
        self._counter = None
        self.val_to_int = None
        self.int_to_val = None
        self.min_seen_count = min_seen_count

    def fit(self, dataset):
        """
        Build the featurizer using the given dataset (DataFrame).
        """
        # Build a map from string feature values to unique integers.
        # Assumes 'other' does not occur as a value.
        self.val_to_int = {'other': 0}
        self.int_to_val = ['other']
        next_index = 1
        self._counter = Counter()
        for list_of_tuples in dataset[self.col_name]:
            self._counter.update(val for val, count in list_of_tuples)
        for val, count in self._counter.iteritems():
            assert val not in self.val_to_int
            if count >= self.min_seen_count:
                self.val_to_int[val] = next_index
                self.int_to_val.append(val)
                next_index += 1
        assert len(self.val_to_int) == next_index
        assert len(self.int_to_val) == next_index

    def transform(self, dataset):
        """
        Featurize the given dataset (DataFrame) and return result as DataFrame.
        """
        feats = np.zeros((len(dataset), len(self.val_to_int)))
        for i, list_of_tuples in enumerate(dataset[self.col_name]):
            for val, count in list_of_tuples:
                if val in self.val_to_int:
                    feats[i][self.val_to_int[val]] = count
                else:
                    feats[i][self.val_to_int['other']] += count
        feat_names = [
            '{} {}'.format(self.col_name, val)
            for val in self.int_to_val]
        return pd.DataFrame(
            feats, index=dataset.index, columns=feat_names)


class BracketingPatternFeaturizer(object):
    """
    Feature recording what brackets occur for a given tube_assembly_id.
    """
    # FIXME:
    # - do min_seen_count in postprocessing, making all the featurizers DRY
    # - decouple building of list-valued features from one-hot- or
    #   count-mapping those features...

    def __init__(self, min_seen_count=10):
        self._counter = None
        self.val_to_int = None
        self.int_to_val = None
        self.min_seen_count = min_seen_count

    def fit(self, dataset):
        grouped = dataset.groupby(
            ['tube_assembly_id', 'supplier', 'quote_date'])
        self._counter = Counter()
        for t_s_q, indices in grouped.groups.iteritems():
            if len(indices) > 1:
                # FIXME: use adj_quantity instead of quantity here.
                bracket = tuple(sorted(dataset.quantity[indices].values))
                self._counter[bracket] += 1

        self.val_to_int = {'other': 0}
        self.int_to_val = ['other']
        next_index = 1
        for val, count in self._counter.iteritems():
            assert val not in self.val_to_int
            if count >= self.min_seen_count:
                self.val_to_int[val] = next_index
                self.int_to_val.append(val)
                next_index += 1
        assert len(self.val_to_int) == next_index
        assert len(self.int_to_val) == next_index

    def transform(self, dataset):
        feats = np.zeros(
            (len(dataset), len(self.val_to_int)), dtype=bool)
        grouped = dataset.groupby(
            ['tube_assembly_id', 'supplier', 'quote_date'])
        for t_s_q, indices in grouped.groups.iteritems():
            if len(indices) > 1:
                # FIXME: use adj_quantity instead of quantity here.
                bracket = tuple(sorted(dataset.quantity[indices].values))
                if bracket in self.val_to_int:
                    feats[indices, self.val_to_int[bracket]] = True
                else:
                    feats[indices, self.val_to_int['other']] = True
        feat_names = [
            'bracketing {}'.format(val)
            for val in self.int_to_val]
        return pd.DataFrame(
            feats, index=dataset.index, columns=feat_names)


class CustomFeaturizer(object):
    """
    Combined featurizer for all features.
    """
    def __init__(self):
        self.featurizers = [
            OneHotFeaturizer('supplier'),
            OneHotFeaturizer('material_id'),
            OneHotFeaturizer('end_a'),
            OneHotFeaturizer('end_x'),
            ListFeaturizer('specs'),
            CountListFeaturizer('components'),
            BracketingPatternFeaturizer(),
        ]

    def fit(self, dataset):
        for featurizer in self.featurizers:
            featurizer.fit(dataset)

    def transform(self, dataset, include_taid=False):
        # Accumulate columns from all the featurizers.
        if self.featurizers:
            dfs = [
                featurizer.transform(dataset)
                for featurizer in self.featurizers]
            result = pd.concat(dfs, axis=1)
        else:
            result = pd.DataFrame()

        # Add features without modification.
        orig_cols = [
            'annual_usage', 'min_order_quantity', 'quantity', 'diameter',
            'length', 'num_bends', 'bend_radius', 'num_boss', 'num_bracket',
        ]
        if include_taid:
            orig_cols.append('tube_assembly_id')
        for col in orig_cols:
            result[col] = dataset[col]

        # Rename some features.
        renamed_cols = {
            'wall': 'wall_thickness',
            'other': 'num_other',
        }
        for col, new_col in renamed_cols.iteritems():
            result[new_col] = dataset[col]

        # Add some binary features.
        bin_cols = {
            'bracket_pricing': 'Yes',
            'end_a_1x': 'Y',
            'end_a_2x': 'Y',
            'end_x_1x': 'Y',
            'end_x_2x': 'Y',
        }
        for col, true_val in bin_cols.iteritems():
            result[col] = (dataset[col] == true_val)

        # Add quote_date feature (convert date to days since 1900-01-01).
        result['quote_date_days_since_1900'] = (
            pd.to_datetime(dataset['quote_date']) - datetime(1900, 1, 1)
        ).astype('timedelta64[D]')

        # Add adj_quantity feature (combining min_order_quantity and quantity).
        result['adj_quantity'] = result[
            ['min_order_quantity', 'quantity']].max(axis=1)

        # Add adj_bracketing feature (whether there really is bracket pricing).
        adj_bracketing = np.zeros(len(dataset), dtype=np.bool)
        grouped = dataset.groupby(
            ['tube_assembly_id', 'supplier', 'quote_date'])
        for t_s_q, indices in grouped.groups.iteritems():
            if len(indices) > 1:
                adj_bracketing[indices] = True
        assert np.all(result.index == dataset.index)
        result['adj_bracketing'] = adj_bracketing

        # TODO:
        # - bend_radius from tube.csv has missing values (9999) for 8 rows;
        #   currently that gets treated as the scalar 9999, which is wrong.
        # - material_id from tube.csv has missing values; currently
        #   OneHotFeaturizer treats missing values as a value `nan` that is
        #   different from 'other' and all the other values. Should we just use
        #   'other' for missing values?
        # - end_a and end_x from tube_csv have missing value 'NONE' and '9999',
        #   which pandas by default treats as two different string values)
        # - handle duplicate specs (e.g. SP-0007); currently ListFeaturizer
        #   just treats them as a single one.
        # - add an `ends` list-valued feature, e.g. [EF-003, EF-006], so that
        #   the info about both ends is merged into a single feature, which
        #   gets converted to num_EF_003, num_EF_006, etc. numerical features.
        # - similarly, add end_1x_count and end_2x count features, treating the
        #   two ends as interchangeable.

        return result
