# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Not
from trytond.transaction import Transaction

__all__ = ['QualityControlTriggerMixin', 'Template']


class QualityControlTriggerMixin(object):

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

            to_create = []
            today = datetime.today()
            for generation_instance in generation_instances:
                test_date = (datetime.combine(self.effective_date,
                        datetime.now().time())
                    if self.effective_date else today)
                to_create.append(QualityTest(
                    test_date=test_date,
                    templates=[template],
                    document=generation_instance))
            with Transaction().set_user(0, set_context=True):
                new_tests += QualityTest.create([x._save_values for x in
                        to_create])

        for test in new_tests:
            with Transaction().set_user(0, set_context=True):
                test.apply_template_values()
                test.save()

        return new_tests

    def _get_quality_trigger_generation_instances(self, template):
        raise NotImplementedError


class Template(metaclass=PoolMeta):
    __name__ = 'quality.template'

    trigger_model = fields.Selection('get_trigger_models', 'Trigger Model',
        help='If you fill in this field, the system will generate a Test '
        'based on this Template when an instance of the selected model was '
        'done. It will generate a test for each instance of Generation '
        'Model in the trigger instance.')
    trigger_generation_model = fields.Selection(
        'get_trigger_generation_models', 'Trigger Generation Model',
        states={
            'invisible': Not(Bool(Eval('trigger_model'))),
            'required': Bool(Eval('trigger_model')),
            },
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
        models = list(
            cls._get_trigger_generation_models_by_trigger_models().keys())
        models = IrModel.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]

    @fields.depends('trigger_model')
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
