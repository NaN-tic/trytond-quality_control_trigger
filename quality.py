# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Not
from trytond.transaction import Transaction

__all__ = ['QualityControlTriggerMixin', 'Template']
__metaclass__ = PoolMeta


class QualityControlTriggerMixin:

    @classmethod
    def create_quality_tests(cls, records, trigger_generation_model):
        pool = Pool()
        QualityTemplate = pool.get('quality.template')

        trigger_templates = QualityTemplate.search([
                ('trigger_model', '=', cls.__name__),
                ('trigger_generation_model', '=', trigger_generation_model),
                ])
        if trigger_templates:
            for record in records:
                record._create_quality_tests(trigger_templates)

    def _create_quality_tests(self, trigger_templates):
        pool = Pool()
        QualityTest = pool.get('quality.test')

        new_tests = []
        for template in trigger_templates:
            generation_instances = (
                self._get_quality_trigger_generation_instances(template))
            if not generation_instances:
                continue

            test_vals = []
            today = datetime.today()
            for generation_instance in generation_instances:
                test_date = (datetime.combine(self.effective_date,
                        datetime.now().time())
                    if self.effective_date else today)
                test_vals.append({
                        'test_date': test_date,
                        'template': template.id,
                        'document': '%s,%d' % (generation_instance.__name__,
                            generation_instance.id)
                        })
            with Transaction().set_user(0, set_context=True):
                new_tests += QualityTest.create(test_vals)

        for test in new_tests:
            with Transaction().set_user(0, set_context=True):
                test.set_template_vals()
                test.save()

        return new_tests

    def _get_quality_trigger_generation_instances(self, template):
        raise NotImplementedError


class Template:
    __name__ = 'quality.template'

    trigger_model = fields.Selection('get_trigger_models', 'Trigger Model',
        help='If you fill in this field, the system will generate a Test '
        'based on this Template when an instance of the selected model was '
        'done. It will generate a test for each instance of Generation '
        'Model in the trigger instance.')
    trigger_generation_model = fields.Selection(
        'get_trigger_generation_models', 'Trigger Generation Model', states={
            'invisible': Not(Bool(Eval('trigger_model'))),
            'required': Bool(Eval('trigger_model')),
            }, selection_change_with=['trigger_model'],
        depends=['trigger_model'])

    @staticmethod
    def default_trigger_model():
        return None

    @staticmethod
    def default_trigger_generation_model():
        return None

    @staticmethod
    def _get_trigger_generation_models_by_trigger_models():
        return {}

    @classmethod
    def get_trigger_models(cls):
        IrModel = Pool().get('ir.model')
        models = cls._get_trigger_generation_models_by_trigger_models().keys()
        models = IrModel.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]

    def get_trigger_generation_models(self):
        IrModel = Pool().get('ir.model')

        if not self.trigger_model:
            return [(None, '')]
        models = self._get_trigger_generation_models_by_trigger_models().get(
            self.trigger_model)
        models = IrModel.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]
