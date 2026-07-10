import csv, json
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.utils import timezone
from datetime import timedelta, date
from django.contrib.auth.decorators import user_passes_test
from .models import Sale, Product, Ingredient, Recipe, FixedExpense, SupplyOrder, Waste

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin, login_url='/admin/login/')
def dashboard(request):
    period = request.GET.get('period', 'month')
    now = timezone.now()
    sales_filtered = Sale.objects.all()
    
    # 1. НАЛАШТУВАННЯ ПЕРІОДУ
    if period == 'day':
        sales_filtered = sales_filtered.filter(sale_date__date=now.date())
        exp_c = 1/30
    elif period == 'week':
        sales_filtered = sales_filtered.filter(sale_date__gte=now - timedelta(days=7))
        exp_c = 1/4
    elif period == 'year':
        sales_filtered = sales_filtered.filter(sale_date__gte=now - timedelta(days=365))
        exp_c = 12
    else: # Month
        sales_filtered = sales_filtered.filter(sale_date__gte=now - timedelta(days=30))
        exp_c = 1

    # 2. ФІНАНСИ ТА ТОЧКА БЕЗЗБИТКОВОСТІ
    rev = sum(float(s.product.price) * s.quantity for s in sales_filtered)
    cost = sum(float(s.product.cost_price) * s.quantity for s in sales_filtered)
    monthly_budget = float(FixedExpense.objects.aggregate(t=Sum('amount'))['t'] or 0)
    current_expenses = round(monthly_budget * exp_c, 2)
    net_profit = round(rev - cost - current_expenses, 2)

    total_cups = sales_filtered.aggregate(t=Sum('quantity'))['t'] or 0
    margin = (rev - cost) / total_cups if total_cups > 0 else 0
    break_even = int(current_expenses / margin) if margin > 0 else 0

    # 3. РОЗПОДІЛЕНИЙ ПРОГНОЗ СКЛАДУ
    stable_forecast = []
    perishable_forecast = []
    all_s = Sale.objects.all()
    first_s = all_s.order_by('sale_date').first()
    days_run = max((now - first_s.sale_date).days + 1 if first_s else 1, 1)

    for ing in Ingredient.objects.all():
        used = sum(s.quantity * r.amount_needed for r in Recipe.objects.filter(ingredient=ing) for s in all_s)
        daily = used / days_run
        vol_left = int(ing.quantity / daily) if daily > 0 else 366
        
        shelf_left = 999
        if ing.is_opened and ing.date_opened:
            shelf_left = max(ing.days_to_expire - (date.today() - ing.date_opened).days, 0)

        res_days = min(vol_left, shelf_left)
        display = "365+" if res_days > 365 else res_days
        status = 'danger' if res_days < 3 else ('warning' if res_days < 7 else 'dark')
        item_data = {'name': ing.name, 'left': display, 'status': status}

        if ing.category in ['coffee', 'milk', 'water']:
            perishable_forecast.append(item_data)
        else:
            stable_forecast.append(item_data)

    # 4. ABC-АНАЛІЗ
    total_op_profit = rev - cost if (rev-cost) > 0 else 1
    product_list = []
    for p in Product.objects.all():
        p_sales = sales_filtered.filter(product=p)
        if p_sales.exists():
            product_list.append({'name': p.name, 'profit': sum(float(s.get_profit()) for s in p_sales)})
    
    product_list.sort(key=lambda x: x['profit'], reverse=True)
    abc_data, running_sum = [], 0
    for p in product_list:
        running_sum += p['profit']
        perc = (running_sum / total_op_profit * 100)
        if perc <= 80: cat, label, css = 'A', 'Лідер прибутку', 'table-success'
        elif perc <= 95: cat, label, css = 'B', 'Стабільний попит', 'table-warning'
        else: cat, label, css = 'C', 'Низька рентабельність', 'table-danger'
        abc_data.append({'name': p['name'], 'profit': round(p['profit'], 2), 'cat': cat, 'label': label, 'class': css})

    # 5. СОРТИ ТА ПЕРСОНАЛ
    coffee_analysis = []
    for ing in Ingredient.objects.filter(category='coffee'):
        prof = sum(float(s.get_profit()) for s in sales_filtered.filter(product__recipes__ingredient=ing).distinct())
        if prof != 0: coffee_analysis.append({'name': ing.name, 'profit': round(prof, 2)})

    baristas = sales_filtered.values('barista__username').annotate(total=Count('id')).order_by('-total')

    # 6. РЕКОМЕНДАЦІЇ DSS
    recommendations = []
    if net_profit < 0: recommendations.append(f"📉 ФІНАНСИ: Збиток {net_profit} грн. Скоротіть витрати або перегляньте ціни.")
    stars = [p['name'] for p in abc_data if p['cat'] == 'A'][:2]
    if stars: recommendations.append(f"🌟 МАРКЕТИНГ: Товари {', '.join(stars)} - ваші лідери. Зробіть на них акцент.")

    # 7. ГРАФІКИ
    stats = sales_filtered.values('product__name').annotate(t=Sum('quantity'))
    
    h_vals = [0]*24
    for e in sales_filtered.annotate(h=ExtractHour('sale_date')).values('h').annotate(c=Count('id')):
        h_vals[e['h']] = e['c']

    weekday_data = sales_filtered.annotate(d=ExtractWeekDay('sale_date')).values('d').annotate(c=Count('id'))
    d_labels = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    d_vals = [0]*7
    for e in weekday_data:
        d_vals[e['d']-1] = e['c']

    return render(request, 'core_logic/dashboard.html', {
        'net_profit': net_profit, 'break_even': break_even, 'abc_data': abc_data, 
        'stable_forecast': stable_forecast, 'perishable_forecast': perishable_forecast,
        'coffee_analysis': coffee_analysis, 'baristas': baristas,
        'recommendations': recommendations, 'expenses': current_expenses,
        'labels': json.dumps([s['product__name'] for s in stats]), 
        'values': json.dumps([s['t'] for s in stats]),
        'h_labels': json.dumps([f"{h}:00" for h in range(24)]), 
        'h_values': json.dumps(h_vals),
        'd_labels': json.dumps(d_labels),
        'd_values': json.dumps(d_vals),
        'period': period
    })

# --- ФУНКЦІЇ ЕКСПОРТУ (ВИПРАВЛЯЮТЬ ВАШУ ПОМИЛКУ) ---

def export_sales_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    response.write(u'\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writerow(['Дата', 'Товар', 'Кількість', 'Бариста', 'Прибуток'])
    for s in Sale.objects.all().order_by('-sale_date'):
        profit = str(round(s.get_profit(), 2)).replace('.', ',')
        writer.writerow([s.sale_date.strftime('%d.%m.%Y %H:%M'), s.product.name, s.quantity, s.barista.username if s.barista else "Admin", profit])
    return response

def export_supplies_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="supplies_report.csv"'
    response.write(u'\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writerow(['Дата', 'Інгредієнт', 'Кількість', 'Статус'])
    for o in SupplyOrder.objects.all().order_by('-order_date'):
        writer.writerow([o.order_date.strftime('%d.%m.%Y'), o.ingredient.name, o.amount, "Отримано" if o.is_received else "Очікується"])
    return response

def export_waste_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="waste_report.csv"'
    response.write(u'\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writerow(['Дата', 'Інгредієнт', 'Кількість', 'Причина'])
    for w in Waste.objects.all().order_by('-date'):
        writer.writerow([w.date.strftime('%d.%m.%Y %H:%M'), w.ingredient.name, w.amount, w.reason])
    return response