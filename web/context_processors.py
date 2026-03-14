from web.models import Category


def categories(request):
    """Inject categories into template context for shared header/nav."""
    return {"categories": list(Category.objects.order_by("name"))}
