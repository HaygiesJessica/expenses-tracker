from rest_framework import serializers
from .models import Expense
from .models import Budget
from django.utils.timezone import now

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['category', 'amount']

    def validate(self, data):
        category = data.get('category')
        current_month = now().month
        current_year = now().year

        existing_budget = Budget.objects.filter(
            category=category,
            date__month=current_month,
            date__year=current_year
        ).first()

        if existing_budget:
            raise serializers.ValidationError(
                {"category": "Budget for this category already exists for this month."}
            )
        
        return data

    def create(self, validated_data):
        validated_data['date'] = now().date()
        return super().create(validated_data)
