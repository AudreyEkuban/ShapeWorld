from itertools import combinations
from random import choice, random, shuffle
from shapeworld import util
from shapeworld.captions import Attribute, EntityType, Selector
from shapeworld.captioners import WorldCaptioner


class UniqueTypeCaptioner(WorldCaptioner):

    def __init__(
        self,
        pragmatical_redundancy_rate=1.0,
        pragmatical_tautology_rate=0.0,
        logical_redundancy_rate=1.0,
        logical_tautology_rate=0.0,
        logical_contradiction_rate=0.0,
        hypernym_rate=0.5
    ):
        super(UniqueTypeCaptioner, self).__init__(
            internal_captioners=(),
            pragmatical_redundancy_rate=pragmatical_redundancy_rate,
            pragmatical_tautology_rate=pragmatical_tautology_rate,
            logical_redundancy_rate=logical_redundancy_rate,
            logical_tautology_rate=logical_tautology_rate,
            logical_contradiction_rate=logical_contradiction_rate
        )

        self.hypernym_rate = hypernym_rate

    def set_realizer(self, realizer):
        if not super(UniqueTypeCaptioner, self).set_realizer(realizer):
            return False

        self.shapes = list(realizer.attributes.get('shape', ()))
        self.colors = list(realizer.attributes.get('color', ()))
        self.textures = list(realizer.attributes.get('texture', ()))
        assert self.shapes or self.colors or self.textures

        return True

    def rpn_length(self):
        return 5

    def rpn_symbols(self):
        return super(UniqueTypeCaptioner, self).rpn_symbols() | \
            set(str(n) for n in range(4)) | \
            {EntityType.__name__} | \
            {'{}-{}-{}'.format(Attribute.__name__, 'shape', value) for value in self.shapes} | \
            {'{}-{}-{}'.format(Attribute.__name__, 'color', value) for value in self.colors} | \
            {'{}-{}-{}'.format(Attribute.__name__, 'texture', value) for value in self.textures}

    def sample_values(self, mode, predication):
        if not super(UniqueTypeCaptioner, self).sample_values(mode=mode, predication=predication):
            return False

        self.valid_attributes = list()
        is_hypernym = 0
        if len(self.shapes) > 1:
            if (self.logical_redundancy or not predication.redundant(predicate='shape')) and (self.logical_contradiction or not predication.blocked(predicate='shape')):
                self.valid_attributes.append('shape')
            else:
                is_hypernym = 1
        if len(self.colors) > 1:
            if (self.logical_redundancy or not predication.redundant(predicate='color')) and (self.logical_contradiction or not predication.blocked(predicate='color')):
                self.valid_attributes.append('color')
            else:
                is_hypernym = 1
        if len(self.textures) > 1:
            if (self.logical_redundancy or not predication.redundant(predicate='texture')) and (self.logical_contradiction or not predication.blocked(predicate='texture')):
                self.valid_attributes.append('texture')
            else:
                is_hypernym = 1

        if not self.logical_tautology and predication.tautological(predicates=self.valid_attributes):
            return False

        assert len(self.valid_attributes) > 0

        self.hypernym = random() < self.hypernym_rate

        shuffle(self.valid_attributes)

        if self.hypernym:
            for _ in range(self.__class__.MAX_SAMPLE_ATTEMPTS):
                self.attributes = choice([list(comb) for n in range(1, len(self.valid_attributes) + int(is_hypernym)) for comb in combinations(self.valid_attributes, n)])
                if not self.logical_tautology and predication.tautological(predicates=self.attributes):
                    continue
                break
            else:
                return False

        else:
            self.attributes = list(self.valid_attributes)

        assert len(self.attributes) > 0

        for predtype in self.attributes:
            predication.apply(predicate=predtype)

        return True

    def incorrect_possible(self):
        return False

    def model(self):
        return util.merge_dicts(
            dict1=super(UniqueTypeCaptioner, self).model(),
            dict2=dict(
                hypernym=self.hypernym,
                attributes=self.attributes
            )
        )

    def caption(self, predication, world):
        if predication.num_agreeing == 0:
            return None

        entities = dict()
        for entity in predication.agreeing:
            entity_attributes = list()
            for predtype in self.attributes:
                if predtype == 'shape':
                    entity_attributes.append(entity.shape.name)
                elif predtype == 'color':
                    entity_attributes.append(entity.color.name)
                elif predtype == 'texture':
                    entity_attributes.append(entity.texture.name)
            entity = tuple(entity_attributes)
            if entity in entities:
                entities[entity] += 1
            else:
                entities[entity] = 1

        entities = [entity for entity, count in entities.items() if count == 1]
        if len(entities) == 0:
            return None

        entity = choice(entities)

        attributes = list()
        for n, predtype in enumerate(self.attributes):
            if predtype == 'shape':
                attributes.append(Attribute(predtype='shape', value=entity[n]))
            elif predtype == 'color':
                attributes.append(Attribute(predtype='color', value=entity[n]))
            elif predtype == 'texture':
                attributes.append(Attribute(predtype='texture', value=entity[n]))

        for n in range(len(attributes) - 1, -1, -1):
            if predication.contradictory(predicate=attributes[n]):
                assert False
            elif not self.pragmatical_redundancy and predication.num_entities > 1 and predication.redundant(predicate=attributes[n]):
                assert False
                attributes.pop(n)

        entity_type = Selector(predtype='unique', scope=EntityType(attributes=attributes))

        entity_type.apply_to_predication(predication=predication)

        return entity_type

    def incorrect(self, caption, predication, world):
        assert False
