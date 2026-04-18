"""
Commande : python manage.py redimensionner_photos
Redimensionne toutes les photos de produits existantes à max 800x800px.
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from boutiques.models import Produit


class Command(BaseCommand):
    help = "Redimensionne toutes les photos produits à max 800x800px"

    def handle(self, *args, **options):
        produits = Produit.objects.exclude(photo="").exclude(photo__isnull=True)
        total = produits.count()
        self.stdout.write(f"{total} photo(s) à traiter...")

        ok = 0
        skipped = 0
        errors = 0

        for p in produits:
            try:
                img = Image.open(p.photo.path)
                w, h = img.width, img.height

                if w <= 800 and h <= 800:
                    skipped += 1
                    continue

                img.thumbnail((800, 800), Image.LANCZOS)
                if img.mode == "RGBA":
                    img = img.convert("RGB")

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85, optimize=True)

                p.photo.save(p.photo.name, ContentFile(buf.getvalue()), save=False)
                Produit.objects.filter(pk=p.pk).update(photo=p.photo.name)

                self.stdout.write(f"  ✓ {p.nom} ({w}x{h} → 800px max)")
                ok += 1

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ✗ {p.nom} : {exc}"))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé : {ok} redimensionnée(s), {skipped} déjà petite(s), {errors} erreur(s)."
        ))
