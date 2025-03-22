from django.urls import path
from .views import *

from .views import add_expense, get_monthly_expense, yearly_summary, set_monthly_budget, get_daily_summary
from .views import search_expenses, category_expense_breakdown, get_highest_expense, get_total_expenses, get_monthly_category_expenses
from .views import get_category_expenditure_current_month, get_expense_summary_by_date, get_expense_history
from .views import get_current_budget, get_budget_status, get_total_budget
from .views import delete_expense, delete_monthly_budget
from .views import update_expense_description
from .views import RegisterUser, LoginUser, SecureView

urlpatterns = [
    path('expenses/add/', add_expense, name='add-expense'),
    path('expenses/summary/month/', get_monthly_expense, name='monthly-expense-summary'),
    path('expenses/yearly-summary/<int:year>/', yearly_summary, name='yearly-summary'),
    path('expenses/category/<str:category>/', get_expense_by_category, name='get-expense-by-category'), 
    path('budget/set/', set_monthly_budget, name='set-monthly-budget'), 
    path('budget/get/', get_current_budget, name='get-current-budget'), 
    path('budget/status/', get_budget_status, name='budget-status'), 
    path('expenses/daily-summary/', get_daily_summary, name='daily-summary'), 
    path('expenses/search/', search_expenses, name='search-expenses'), 
    path('expenses/category-breakdown/', category_expense_breakdown, name='category-expense-breakdown'), 
    path('expenses/highest/', get_highest_expense, name='get-highest-expense'), 
    path('expenses/total/', get_total_expenses, name='get-total-expenses'), 
    path('expenses/monthly-category/', get_monthly_category_expenses, name='get-monthly-category-expenses'), 
    path('expenses/category-current-month/', get_category_expenditure_current_month, name='get-category-expenditure-current-month'),
    path('expenses/summary-by-date/', get_expense_summary_by_date, name='get-expense-summary-by-date'), 
    path('expenses/history/', get_expense_history, name='get-expense-history'), 
    path('expenses/<int:expense_id>/', delete_expense, name='delete-expense'), 
    path('expenses/<int:expense_id>/description/', update_expense_description, name='update-expense-description'), 
    path('expenses/budget/total/', get_total_budget, name='total_budget_for_all_categories'),
    path('expenses/monthly/', get_monthly_category_expenses, name='monthly-category-expenses'), 
    path('budget/delete/<str:category>/', delete_monthly_budget, name='delete_monthly_budget'),
    path("register/", RegisterUser.as_view(), name="register"),
    path("login/", LoginUser.as_view(), name="login"),
    path("secure/", SecureView.as_view(), name="secure"),
]
