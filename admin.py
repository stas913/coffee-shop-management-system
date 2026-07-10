from django.contrib import admin
from .models import Ingredient, Product, Sale, Recipe, SupplyOrder, FixedExpense, Waste

# 1. Рецепти всередині товарів (Inline)
class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 2

# 2. Налаштування товарів
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'cost_price')
    inlines = [RecipeInline]

# 3. Налаштування інгредієнтів
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'unit', 'purchase_price', 'is_opened')
    list_filter = ('category', 'is_opened')

# 4. Налаштування продажів
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'barista', 'sale_date')
    list_filter = ('barista', 'sale_date')
    
    def save_model(self, request, obj, form, change):
        if not obj.barista:
            obj.barista = request.user
        super().save_model(request, obj, form, change)

# 5. Налаштування замовлень постачальникам
@admin.register(SupplyOrder)
class SupplyOrderAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'amount', 'is_received', 'order_date')
    list_editable = ('is_received',)

# 6. Постійні витрати (Оренда тощо)
@admin.register(FixedExpense)
class FixedExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'date')

# 7. Новий розділ: СПИСАННЯ (WASTE)
@admin.register(Waste)
class WasteAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'amount', 'reason', 'date')
    list_filter = ('ingredient', 'date', 'reason')

# Реєструємо Recipe один раз (якщо ти хочеш бачити їх окремим списком)
admin.site.register(Recipe)