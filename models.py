from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class Ingredient(models.Model):
    CATEGORY_CHOICES = [
        ('coffee', 'Кавове зерно (Сорти)'),
        ('milk', 'Молоко'),
        ('water', 'Вода'),
        ('packing', 'Пакування (стакани, кришки)'),
        ('other', 'Інше (цукор, сиропи)'),
    ]

    name = models.CharField("Назва інгредієнта", max_length=100)
    category = models.CharField("Категорія", max_length=20, choices=CATEGORY_CHOICES, default='other')
    quantity = models.FloatField("Залишок на складі")
    unit = models.CharField("Одиниця виміру (г, мл, шт)", max_length=10)
    purchase_price = models.DecimalField("Ціна закупівлі (за 1 од.)", max_digits=10, decimal_places=4, default=0)
    min_limit = models.FloatField("Мінімальний поріг (сповіщення)", default=10)
    monthly_supply_amount = models.FloatField("Планова кількість для закупівель", default=0)

    # КОНТРОЛЬ ЯКОСТІ ТА СВІЖОСТІ
    is_opened = models.BooleanField("Тара відкрита?", default=False)
    date_opened = models.DateField("Дата відкриття тари", null=True, blank=True)
    days_to_expire = models.IntegerField("Термін придатності після відкриття (днів)", default=7)

    class Meta:
        verbose_name = "Інгредієнт"
        verbose_name_plural = "Склад (Інгредієнти)"

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class Product(models.Model):
    name = models.CharField("Назва напою", max_length=100)
    price = models.DecimalField("Ціна продажу", max_digits=10, decimal_places=2)

    @property
    def cost_price(self):
        total_cost = 0.0
        for item in self.recipes.all():
            total_cost += float(item.ingredient.purchase_price) * item.amount_needed
        return round(total_cost, 2)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Меню (Товари)"

    def __str__(self):
        return f"{self.name} (Собівартість: {self.cost_price} грн)"


class Recipe(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipes')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount_needed = models.FloatField("Кількість на 1 порцію")

    class Meta:
        verbose_name = "Елемент рецепта"
        verbose_name_plural = "Рецептури"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Кількість", default=1)
    barista = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Бариста")
    sale_date = models.DateTimeField("Дата продажу", auto_now_add=True)

    def get_profit(self):
        return (float(self.product.price) - float(self.product.cost_price)) * self.quantity

    def clean(self):
        recipe_items = Recipe.objects.filter(product=self.product)
        if not recipe_items.exists():
            raise ValidationError(f"Для товару {self.product.name} не налаштовано рецепт!")
        for item in recipe_items:
            needed = item.amount_needed * self.quantity
            if item.ingredient.quantity < needed:
                raise ValidationError(f"НЕДОСТАТНЬО РЕСУРСІВ: {item.ingredient.name}. Треба: {needed}, є: {item.ingredient.quantity}")

    def save(self, *args, **kwargs):
        self.full_clean() 
        recipe_items = Recipe.objects.filter(product=self.product)
        for item in recipe_items:
            item.ingredient.quantity -= (item.amount_needed * self.quantity)
            item.ingredient.save()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Продаж"
        verbose_name_plural = "Продажі"


class SupplyOrder(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Інгредієнт")
    amount = models.FloatField("Кількість у замовленні")
    is_received = models.BooleanField("Товар отримано (поповнити склад)", default=False)
    order_date = models.DateTimeField("Дата створення", auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_order = SupplyOrder.objects.get(pk=self.pk)
            if not old_order.is_received and self.is_received:
                self.ingredient.quantity += self.amount
                self.ingredient.save()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення постачальникам"


class FixedExpense(models.Model):
    name = models.CharField("Стаття витрат (Оренда, Світло тощо)", max_length=100)
    amount = models.DecimalField("Сума", max_digits=10, decimal_places=2)
    date = models.DateField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Фіксована витрата"
        verbose_name_plural = "Постійні витрати"


class Waste(models.Model):
    """Нова модель: Списання браку або розливу"""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Інгредієнт")
    amount = models.FloatField("Кількість списання")
    reason = models.CharField("Причина", max_length=255)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Списання"
        verbose_name_plural = "Списання (Брак/Втрати)"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.ingredient.quantity -= self.amount
            self.ingredient.save()
        super().save(*args, **kwargs)