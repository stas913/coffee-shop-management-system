from .models import Sale, Product, Ingredient
from django.db.models import Sum

def run_business_analysis():
    print("\n" + "="*50)
    print("   ІНТЕЛЕКТУАЛЬНА СИСТЕМА АНАЛІЗУ (BI-MODULE 126)")
    print("="*50)
    
    sales = Sale.objects.all()
    if not sales.exists():
        print("Дані відсутні.")
        return

    # 1. Фінансові метрики
    total_revenue = sum(float(s.product.price) * s.quantity for s in sales)
    total_costs = sum(float(s.product.cost_price) * s.quantity for s in sales)
    total_profit = total_revenue - total_costs

    print(f"💰 Виручка: {total_revenue:.2f} грн | Прибуток: {total_profit:.2f} грн")
    print("-" * 50)

    # 2. ABC-АНАЛІЗ (Логіка аналізу бізнес-процесів)
    product_stats = []
    for product in Product.objects.all():
        # Скільки всього заробили на цьому конкретному товарі
        product_sales = Sale.objects.filter(product=product)
        p_profit = sum(s.get_profit() for s in product_sales)
        if p_profit > 0:
            product_stats.append({'name': product.name, 'profit': p_profit})

    # Сортуємо за прибутком (від більшого до меншого)
    product_stats.sort(key=lambda x: x['profit'], reverse=True)

    print("📊 ABC-АНАЛІЗ АСОРТИМЕНТУ:")
    cumulative_profit = 0
    for item in product_stats:
        cumulative_profit += item['profit']
        share = (cumulative_profit / total_profit) * 100
        
        if share <= 80:
            category = "🅰️ (TOP)"
        elif share <= 95:
            category = "🅱️ (MEDIUM)"
        else:
            category = "🅲 (LOW EFFICIENCY)"
        
        print(f"  {category} {item['name']}: {item['profit']:.2f} грн")

    print("-" * 50)
    
    # 3. СТАН СКЛАДУ
    print("🚨 КРИТИЧНІ ЗАПАСИ:")
    for ing in Ingredient.objects.all():
        if ing.quantity <= ing.min_limit:
            print(f"  ❌ ТРЕБА КУПИТИ: {ing.name} (залишок: {ing.quantity} {ing.unit})")
    
    print("="*50 + "\n")