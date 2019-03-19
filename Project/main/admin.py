from datetime import datetime, timedelta
import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from django import forms
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.template.response import TemplateResponse

from django.db.models.functions import TruncDay
from django.db.models import Avg, Count, Min, Sum

from . import models

logger = logging.getLogger(__name__)


def make_active(self, request, queryset):
    queryset.update(active=True)


def make_inactive(self, request, queryset):
    queryset.update(active=False)


make_active.short_description = "Mark selected items as active"
make_inactive.short_description = "Mark selected item as inactive"


class ProductAdmin(admin.ModelAdmin):
    """
    Just in case you don't know it

    The simpler ones
        list_display    what to show
        list_filter     filtering by what

    A bit more interesting ones
        list_editable   you could "edit" it on-the-fly (& "save" it, btn exists)
        search_fields   kinda the 'keyword' you're searching for (e.g. "By Title")

    About `search_fields`
        it could use the QuerySet as well (based on the examples),
        since we often need cross-table queries (which is reasonable!).

        e.g.
            search_fields = ("product__name",)

    About `actions`
        the default one is "Delete selected YOUR_MODEL_NAME_LOWERCASE"
        we could add our own & then add those by <overriding `actions` attr>.
    """

    list_display = ("name", "slug", "in_stock", "price")
    list_filter = ("active", "in_stock", "date_updated")
    list_editable = ("in_stock",)
    search_fields = ("name",)
    prepopulated_fields = { "slug": ("name",) }

    autocomplete_fields = ("tags",)

    actions = [make_active, make_inactive]

    def get_readonly_fields(self, request, obj = None):
        """
        Limit the <ability to change [SLUG]> to the owners of company only.

        Review of `readonly_fields`
        || Typically, the field itself was generated by other fields.
        || e.g. The `thumbnail` field in the `ProductImage` part.
        """

        if request.user.is_superuser:
            return self.readonly_fields
        return list(self.readonly_fields) + ["slug", "name"]

    def get_prepopulated_fields(self, request, obj = None):
        """
        This method works with the `get_readonly_fields` (not always, of course).
        """

        if request.user.is_superuser:
            return self.prepopulated_fields
        else:
            return { }


class DispatchersProductAdmin(ProductAdmin):
    readonly_fields = ("description", "price", "tags", "active")
    prepopulated_fields = { }
    autocomplete_fields = ()


class ProductTagAdmin(admin.ModelAdmin):
    """
    Just in case you don't know it :D

    prepopulated_fields     auto generating based on other fields
    autocomplete_fields     kinda like dropdown-list (based on ur "products")
    """

    list_display = ("name", "slug")
    list_filter = ("active",)
    search_fields = ("name",)
    prepopulated_fields = { "slug": ("name",) }

    # autocomplete_fields = ("products",)

    def get_readonly_fields(self, request, obj = None):
        if request.user.is_superuser:
            return self.readonly_fields
        return list(self.readonly_fields) + ["slug", "name"]

    def get_prepopulated_fields(self, request, obj = None):
        if request.user.is_superuser:
            return self.prepopulated_fields
        else:
            return { }


class ProductImageAdmin(admin.ModelAdmin):
    """
    Just in case you don't know it :D
        readonly_fields     you can't modify it ('autogen-thumb' for our cases)

    The generated thumbnails still NOT displaying (on admin site).
    You'll need to edit 'booktime/urls.py'
        append something like `settings.MEDIA_URL` to the `urlpatterns`.
    """

    list_display = ("thumbnail_tag", "product_name")
    readonly_fields = ("thumbnail",)
    search_fields = ("product__name",)

    def thumbnail_tag(self, obj):
        if obj.thumbnail:
            return format_html('<img src="%s"' % obj.thumbnail.url)
        return "-"

    # The title which is displayed
    #   on the 'localhost:8000/admin/main/productimage/'
    thumbnail_tag.short_description = "Thumbnail"

    def product_name(self, obj):
        return obj.product.name  # might be cross-table-querying related??


class UserAdmin(DjangoUserAdmin):
    """
    Q & A
        What does `fieldsets` (here) for?
        =>  Define the fields that'll be displayed on the 'create user' page.

        What does `add_fieldsets` for?
        =>  Define the fields that'll be displayed on the 'new user' page.

    Quote
        Those two tuples specify what fields to present in the “change model” page
        and in the “add model” page, along with the names of the page sections.

        If these were not present, for any other model,
        Django would make every field changeable. The built-in DjangoUserAdmin, however,
        introduces some customizations to the default behavior that need to be undone.
    """

    fieldsets = (
        (
            None, { "fields": ("email", "password") }
        ),
        (
            "Personal info", { "fields": ("first_name", "last_name") },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("email",)


class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "address1",
        "address2",
        "city",
        "country",
    )
    readonly_fields = ("user",)


class BasketLineInline(admin.TabularInline):
    model = models.BasketLine
    raw_id_fields = ("product",)


class BasketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "count")
    list_editable = ("status",)
    list_filter = ("status",)
    inlines = (BasketLineInline,)


class OrderLineInline(admin.TabularInline):
    model = models.OrderLine
    raw_id_fields = ("product",)


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status")
    list_editable = ("status",)
    list_filter = ("status", "shipping_country", "date_added")

    inlines = (OrderLineInline,)

    fieldsets = (
        (
            "None", { "fields": ("user", "status") }
        ),
        (
            "Billing info",
            {
                "fields": (
                    "billing_name",
                    "billing_address1",
                    "billing_address2",
                    "billing_zip_code",
                    "billing_city",
                    "billing_country",
                )
            }
        ),
        (
            "Shipping info",
            {
                "fields": (
                    "shipping_name",
                    "shipping_address1",
                    "shipping_address2",
                    "shipping_zip_code",
                    "shipping_city",
                    "shipping_country",
                )
            }
        )
    )


# ********************-----**********************
# ******************* Roles *********************
# ********************-----**********************


class CentralOfficeOrderLineInline(admin.TabularInline):
    model = models.OrderLine
    readonly_fields = ("product",)


class CentralOfficeOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status")
    list_editable = ("status",)
    readonly_fields = ("user",)
    list_filter = ("status", "shipping_country", "date_added")
    inlines = (CentralOfficeOrderLineInline,)

    fieldsets = (
        (None, { "fields": ("user", "status") }),
        (
            "Billing info",
            {
                "fields": (
                    "billing_name",
                    "billing_address1",
                    "billing_address2",
                    "billing_zip_code",
                    "billing_city",
                    "billing_country",
                )
            },
        ),
        (
            "Shipping info",
            {
                "fields": (
                    "shipping_name",
                    "shipping_address1",
                    "shipping_address2",
                    "shipping_zip_code",
                    "shipping_city",
                    "shipping_country",
                )
            },
        ),
    )


class DispatchersOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shipping_name",
        "date_added",
        "status",
    )
    list_filter = ("status", "shipping_country", "date_added")
    inlines = (CentralOfficeOrderLineInline,)

    fieldsets = (
        (
            "Shipping info",
            {
                "fields": (
                    "shipping_name",
                    "shipping_address1",
                    "shipping_address2",
                    "shipping_zip_code",
                    "shipping_city",
                    "shipping_country",
                )
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.filter(status=models.Order.PAID)


# ********************-----**********************
# *************** Helper & Extra ****************
# ********************-----**********************


class PeriodSelectForm(forms.Form):
    PERIODS = (
        (30, "30 days"),
        (60, "60 days"),
        (90, "90 days"),
    )

    period = forms.TypedChoiceField(
        choices=PERIODS,
        coerce=int,
        required=True
    )


class ColoredAdminSite(admin.sites.AdminSite):
    def each_context(self, request):
        context = super().each_context(request)

        context["site_header_color"] = getattr(
            self, "site_header_color", None
        )
        context["module_caption_color"] = getattr(
            self, "module_caption_color", None
        )

        return context


class ReportingColoredAdminSite(ColoredAdminSite):
    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path(
                "orders_per_day/",
                self.admin_view(self.orders_per_day),
            ),
            path(
                "most_bought_products/",
                self.admin_view(self.most_bought_products),
                name="most_bought_products",
            ),
        ]

        return my_urls + urls

    def orders_per_day(self, request):
        """
        About the `datetime.now` issue (warning was raised)
            Check this post
                TITLE   RuntimeWarning: DateTimeField received a naive datetime
                LINK    https://stackoverflow.com/a/45080605/6273859 (one of them)
        """

        starting_day = datetime.now(tz=timezone.utc) - timedelta(days=180)
        order_data = (
            models.Order.objects
                .filter(date_added__gt=starting_day)
                .annotate(day=TruncDay("date_added"))
                .values("day")
                .annotate(c=Count("id"))
        )

        # These two provide data for plotting purposes,
        # that is used by a JavaScript library (i.e. Chart.js).
        labels = [
            x["day"].strftime("%Y-%d-%d")
            for x in order_data
        ]
        values = [x["c"] for x in order_data]

        # Make the templates could use the data
        context = dict(
            self.each_context(request),
            title="Orders per day",
            labels=labels,
            values=values,
        )

        return TemplateResponse(
            request, "orders_per_day.html", context
        )

    def most_bought_products(self, request):
        if request.method == "POST":
            form = PeriodSelectForm(request.POST)

            if form.is_valid():
                pd_days = form.cleaned_data["period"]
                starting_day = datetime.now(tz=timezone.utc) - timedelta(days=pd_days)

                data = (
                    models.OrderLine.objects
                        .filter(order__date_added__gt=starting_day)
                        .values("product__name")
                        .annotate(c=Count("id"))
                )

                logger.info(
                    "most_bought_products query: [%s]",
                    data.query
                )

                labels = [x["product__name"] for x in data]
                values = [x["c"] for x in data]

        else:
            form = PeriodSelectForm()

            labels = None
            values = None

        context = dict(
            self.each_context(request),
            title="Most bought products",
            form=form,
            labels=labels,
            values=values,
        )

        return TemplateResponse(
            request, "most_bought_products.html", context
        )

    def index(self, request, extra_context = None):
        reporting_pages = [
            {
                "name": "Orders per day",
                "link": "orders_per_day/",
            },
            {
                "name": "Most bought products",
                "link": "most_bought_products/",
            },
        ]

        if not extra_context:
            extra_context = { }

        extra_context = { "reporting_pages": reporting_pages }

        return super().index(request, extra_context)


# ********************-----**********************
# **************** Style & Perm *****************
# ********************-----**********************


class OwnersAdminSite(ReportingColoredAdminSite):
    site_header = "BookTime owners administration"
    site_header_color = "black"
    module_caption_color = "grey"

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_superuser
        )


class CentralOfficesAdminSite(ReportingColoredAdminSite):
    site_header = "BookTime central office administration"
    site_header_color = "purple"
    module_caption_color = "pink"

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_employee
        )


class DispatchersAdminSite(ReportingColoredAdminSite):
    site_header = "BookTime dispatch administration"
    site_header_color = "green"
    module_caption_color = "lightgreen"

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_dispatcher
        )


# ********************-----**********************
# ****************** Register *******************
# ********************-----**********************


main_admin = OwnersAdminSite()
central_office_admin = CentralOfficesAdminSite("central-office-admin")
dispatchers_admin = DispatchersAdminSite("dispatchers-admin")

main_admin.register(models.User, UserAdmin)
main_admin.register(models.Product, ProductAdmin)
main_admin.register(models.ProductTag, ProductTagAdmin)
main_admin.register(models.ProductImage, ProductImageAdmin)
main_admin.register(models.Address, AddressAdmin)
main_admin.register(models.Basket, BasketAdmin)
main_admin.register(models.Order, OrderAdmin)

central_office_admin.register(models.Product, ProductAdmin)
central_office_admin.register(models.ProductTag, ProductTagAdmin)
central_office_admin.register(models.ProductImage, ProductImageAdmin)
central_office_admin.register(models.Address, AddressAdmin)
central_office_admin.register(models.Order, CentralOfficeOrderAdmin)

dispatchers_admin.register(models.Product, DispatchersProductAdmin)
dispatchers_admin.register(models.ProductTag, ProductTagAdmin)
dispatchers_admin.register(models.Order, DispatchersOrderAdmin)