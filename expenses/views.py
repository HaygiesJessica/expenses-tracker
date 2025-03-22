from datetime import datetime

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils.timezone import now
from django.http import JsonResponse

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from .models import Expense, Budget
from .serializers import ExpenseSerializer, BudgetSerializer

# 1st Endpoint: Add a New Expense
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_expense(request):
    data = request.data.copy()  
    data['user'] = request.user.id

    serializer = ExpenseSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2nd Endpoint: Get Monthly Expense Summary
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_monthly_expense(request):
    today = now()
    current_month, current_year = today.month, today.year
    total = Expense.objects.filter(
        user=request.user,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    return Response({"monthly_expense": total}, status=200)

# 3rd Endpoint: Get Yearly Expense Summary
@api_view(["GET"])
@authentication_classes([TokenAuthentication])  
@permission_classes([IsAuthenticated]) 
def yearly_summary(request, year):
    total_expense = Expense.objects.filter(user=request.user, date__year=year).aggregate(Sum("amount"))

    print(f"User: {request.user}, Year: {year}, Expenses Found: {total_expense}")  
    
    return Response({"yearly_expense": total_expense["amount__sum"] or 0.0})

# 4th Endpoint: Get Expense by Category
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_expense_by_category(request, category):
    expenses = Expense.objects.filter(user=request.user, category=category)
    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data)

#5th Endpoint: Set Monthly Budget
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def set_monthly_budget(request):
    serializer = BudgetSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    category = serializer.validated_data['category']
    budget_amount = serializer.validated_data['amount']
    current_date = now().date()

    # Ensure filtering by user
    budget, created = Budget.objects.update_or_create(
        user=request.user,
        category=category,
        date__year=current_date.year,
        date__month=current_date.month,
        defaults={'amount': budget_amount}
    )

    return Response({
        "message": "Budget set successfully",
        "category": category,
        "amount": budget.amount,
        "month": current_date.strftime('%B'),
        "year": current_date.year
    }, status=status.HTTP_201_CREATED)

# 6th Endpoint: Get Current Budget
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_current_budget(request):
    """Retrieve the latest budget for the authenticated user and a specific category."""
    category = request.GET.get('category')

    if not category:
        return Response({"error": "Category is required"}, status=400)

    try:
        budget = Budget.objects.filter(
            user=request.user, 
            category=category
        ).order_by('-date').first()

        if not budget:
            return Response({"error": "No budget found for this category"}, status=404)

        return Response({
            "category": budget.category,
            "budget_amount": budget.amount,
            "date": budget.date.strftime('%Y-%m-%d'),
        }, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
# 7th Endpoint: Track Spending Against Budget
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_budget_status(request):
    """Check user's spending against budget for a specific category in the current month."""
    category = request.GET.get('category')

    if not category:
        return Response({'error': 'Category parameter is required'}, status=400)

    budget = Budget.objects.filter(
        user=request.user,
        category=category
    ).order_by('-date').first()

    if not budget:
        return Response({'error': 'No budget found for this category'}, status=404)

    current_month = now().month
    total_spent = Expense.objects.filter(
        user=request.user,
        category=category,
        date__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    remaining_budget = budget.amount - total_spent
    status = "Under Budget" if remaining_budget >= 0 else "Over Budget"

    return Response({
        'category': category,
        'budget_amount': budget.amount,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'status': status
    })

# 8th Endpoint: Get Total Expenses for a Specific Day
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_daily_summary(request):

    date = request.GET.get('date', '').strip()  # Remove spaces and newlines

    if not date:
        return Response({'error': 'Date parameter is required'}, status=400)

    try:
        print(f"Received date: {repr(date)}")
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)

    daily_expenses = Expense.objects.filter(user=request.user, date=selected_date)

    total_spent = daily_expenses.aggregate(total=Sum('amount'))['total'] or 0

    expenses_list = [
        {
            "date": str(exp.date),
            "category": exp.category,
            "amount": str(exp.amount),  
            "description": exp.description or None  
        }
        for exp in daily_expenses
    ]

    return Response({
        "date": str(selected_date),
        "total_spent": str(total_spent), 
        "expenses": expenses_list
    }, status=200)

# 9th Endpoint: Search Expenses by Date Range
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def search_expenses(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return Response({'error': 'Both start_date and end_date are required'}, status=400)

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start_date > end_date:
            return Response({'error': 'start_date cannot be after end_date'}, status=400)
    except ValueError:
        return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)
    
    expenses = Expense.objects.filter(user=request.user, date__range=[start_date, end_date])

    if not expenses.exists():
        return Response({'message': 'No expenses found in the given date range'})

    total_spent = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    expenses_list = [
        {"date": str(exp.date), "category": exp.category, "amount": exp.amount, "description": exp.description}
        for exp in expenses
    ]

    return Response({
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_spent": total_spent,
        "expenses": expenses_list
    })

# 10th Endpoint: Get Category-wise Expense Breakdown
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def category_expense_breakdown(request):

    breakdown = (
        Expense.objects.filter(user=request.user)
        .values("category")
        .annotate(total_amount=Sum("amount"))
        .order_by("-total_amount")  
    )

    breakdown_list = list(breakdown)

    return Response({
        "total_categories": len(breakdown_list),
        "breakdown": breakdown_list
    })

# 11th Endpoint: Get Most Expensive Expense
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_highest_expense(request):
    """Retrieve the highest expense for the authenticated user."""
    
    highest_expense = (
        Expense.objects.filter(user=request.user)
        .order_by('-amount')
        .first()
    )

    if not highest_expense:
        return Response({"message": "No expenses found for this user"}, status=404)

    return Response({
        "category": highest_expense.category,
        "amount": highest_expense.amount,
        "date": highest_expense.date.strftime("%Y-%m-%d")
    })

#12th Endpoint: Calculate Total Expenses for a Category
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_total_expenses(request):

    category = request.query_params.get('category')

    if not category:
        return Response({'error': 'Category parameter is required'}, status=400)

    filtered_expenses = Expense.objects.filter(user=request.user, category__iexact=category)

    total = filtered_expenses.aggregate(total=Sum('amount'))['total']

    return Response({
        'category': category,
        'total_expenses': total if total else 0,  
    }, status=200)

#13th Endpoint: Get Total Expenses for All Categories
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_monthly_category_expenses(request):
    
    category = request.GET.get('category')

    if not category:
        return Response({"error": "Category parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    today = now()
    current_month_expenses = Expense.objects.filter(
        user=request.user, 
        category__iexact=category,
        date__year=today.year,
        date__month=today.month
    )

    total_expense = current_month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    return Response({
        "category": category,
        "total_expenses_this_month": total_expense
    }, status=status.HTTP_200_OK)

# 14th Endpoint: Get Category Expenditure for Current Month
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_category_expenditure_current_month(request):
    
    category = request.GET.get("category")

    if not category:
        return Response({"error": "Category is required"}, status=status.HTTP_400_BAD_REQUEST)

    today = now()
    current_month = today.month
    current_year = today.year

    total = Expense.objects.filter(
        user=request.user,  
        category__iexact=category,
        date__month=current_month,
        date__year=current_year
    ).aggregate(total_amount=Sum("amount"))

    return Response({
        "category": category,
        "month": today.strftime("%B"),  
        "year": current_year,
        "total_expense": total["total_amount"] or 0
    }, status=status.HTTP_200_OK)

# 15th Endpoint: Get Expense Summary by Date
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_expense_summary_by_date(request):

    date_str = request.GET.get("date")
    
    if not date_str:
        return Response({"error": "Date is required (format: YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

    expenses = Expense.objects.filter(user=request.user, date=target_date)

    summary = {
        "date": target_date.strftime("%Y-%m-%d"),
        "total_expense": expenses.aggregate(total_amount=Sum('amount'))["total_amount"] or 0,
        "expenses": [
            {
                "id": expense.id,
                "category": expense.category,
                "amount": str(expense.amount),  
                "description": expense.description if hasattr(expense, 'description') else None
            }
            for expense in expenses
        ]
    }

    return Response(summary, status=status.HTTP_200_OK)

# 16th Endpoint: Get Expense History for a Category
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_expense_history(request):

    category = request.GET.get('category', None)

    if not category:
        return Response({"error": "Category parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    expenses = Expense.objects.filter(user=request.user, category__iexact=category).order_by('date')

    if not expenses.exists():
        return Response({"message": f"No expenses found for category '{category}'"}, status=status.HTTP_404_NOT_FOUND)

    expense_data = [
        {
            "id": exp.id,
            "amount": str(exp.amount),  
            "category": exp.category,
            "description": exp.description if hasattr(exp, 'description') else None,
            "date": exp.date.strftime("%Y-%m-%d"),
        }
        for exp in expenses
    ]

    return Response({
        "category": category,
        "total_expenses": expenses.aggregate(Sum('amount'))["amount__sum"] or 0,
        "history": expense_data
    }, status=status.HTTP_200_OK)

# 17th Endpoint: Delete Specific Expense
@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_expense(request, expense_id):

    try:
        expense = Expense.objects.get(id=expense_id, user=request.user)
    except Expense.DoesNotExist:
        return Response({"error": f"Expense with ID {expense_id} not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

    deleted_expense = {
        "id": expense.id,
        "category": expense.category,
        "amount": str(expense.amount),
        "date": expense.date.strftime("%Y-%m-%d"),
        "description": expense.description if hasattr(expense, 'description') else None
    }

    expense.delete()

    return Response({
        "message": f"Expense with ID {expense_id} has been deleted",
        "deleted_expense": deleted_expense
    }, status=status.HTTP_200_OK)

# 18th Endpoint: Update Expense Description
@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_expense_description(request, expense_id):

    new_description = request.data.get("new_description")
    if not new_description:
        return Response({"error": "New description is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        expense = Expense.objects.get(id=expense_id, user=request.user)
    except Expense.DoesNotExist:
        return Response({"error": f"Expense with ID {expense_id} not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

    old_description = expense.description

    expense.description = new_description
    expense.save()

    return Response({
        "message": f"Description for expense ID {expense_id} has been updated",
        "updated_expense": {
            "id": expense.id,
            "category": expense.category,
            "amount": str(expense.amount),
            "date": expense.date.strftime("%Y-%m-%d"),
            "old_description": old_description,
            "new_description": expense.description
        }
    }, status=status.HTTP_200_OK)

# 19th Endpoint: Get Total Budget for All Categories
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_total_budget(request):

    total_budget = Budget.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or 0

    return Response({"total_budget": total_budget}, status=200)

# 20th Endpoint: Get Monthly Spend for Each Category
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_monthly_category_expenses(request):

    today = now()
    current_month, current_year = today.month, today.year

    user_expenses = Expense.objects.filter(
        user=request.user,
        date__year=current_year,
        date__month=current_month
    )

    if not user_expenses.exists():
        return Response({"message": "No expenses found for the current month"}, status=404)

    expenses = user_expenses.values('category').annotate(total_spent=Sum('amount'))
    total_expenses = user_expenses.aggregate(total=Sum('amount'))['total'] or 0  # Summing all expenses

    return Response({
        "month": today.strftime('%B %Y'),
        "category_expenses": list(expenses),
        "total_expenses": total_expenses  # Adding total expenses
    }, status=200)

# Additional Endpoint: Delete Monthly Budget
@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_monthly_budget(request, category):

    current_date = now().date()

    try:
        budget = Budget.objects.get(
            user=request.user, 
            category__iexact=category,
            date__year=current_date.year,
            date__month=current_date.month
        )
        budget.delete()
        return Response({"message": "Budget deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    except Budget.DoesNotExist:
        return Response({"error": "Budget not found"}, status=status.HTTP_404_NOT_FOUND)

class RegisterUser(APIView):
    permission_classes = [AllowAny]  

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email")

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"message": "User registered successfully", "token": token.key}, status=status.HTTP_201_CREATED)
    
class LoginUser(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({"message": "Login successful", "token": token.key}, status=status.HTTP_200_OK)
       
class SecureView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Hello, authenticated user!"})
