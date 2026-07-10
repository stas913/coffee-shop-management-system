from django.contrib import admin
from django.urls import path
from core_logic.views import dashboard, export_sales_csv, export_supplies_csv, export_waste_csv

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard),
    path('export/', export_sales_csv),
    path('export-supplies/', export_supplies_csv),
    path('export-waste/', export_waste_csv),
]