"""
Formulaires d'automatisation pour les commerçants Fëgg Jaay.
"""

from django import forms
from django.contrib.auth.models import User
from boutiques.models import Boutique


class CommercantAutoConfigForm(forms.ModelForm):
    """Formulaire simple pour que les commerçants configurent leur WhatsApp Business avec Infobip."""

    email = forms.EmailField(
        label="Email professionnel",
        help_text="Pour recevoir les instructions de configuration",
        required=True
    )

    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        help_text="Pour accéder à votre dashboard",
        required=True
    )

    password_confirm = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput,
        required=True
    )

    accept_terms = forms.BooleanField(
        label="J'accepte les conditions d'utilisation",
        required=True
    )

    class Meta:
        model = Boutique
        fields = ['nom', 'telephone_wa', 'proprietaire_tel', 'ville']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Nom de votre boutique', 'class': 'form-control'}),
            'telephone_wa': forms.TextInput(attrs={'placeholder': '221771234567', 'class': 'form-control'}),
            'proprietaire_tel': forms.TextInput(attrs={'placeholder': '221771234567', 'class': 'form-control'}),
            'ville': forms.TextInput(attrs={'placeholder': 'Dakar', 'value': 'Dakar', 'class': 'form-control'}),
        }

    def clean_telephone_wa(self):
        """Validation du format du numéro WhatsApp."""
        phone = self.cleaned_data['telephone_wa']
        phone = phone.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('221'):
            raise forms.ValidationError("Le numéro doit commencer par l'indicatif du Sénégal (221)")
        if len(phone) != 12:
            raise forms.ValidationError("Le numéro doit avoir 12 chiffres (221 + 9 chiffres)")

        # Vérifier si le numéro est déjà utilisé
        if Boutique.objects.filter(telephone_wa=phone).exists():
            raise forms.ValidationError("Ce numéro WhatsApp est déjà utilisé par une autre boutique.")

        return phone

    def clean_proprietaire_tel(self):
        """Validation du format du numéro personnel."""
        phone = self.cleaned_data['proprietaire_tel']
        phone = phone.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('221'):
            raise forms.ValidationError("Le numéro doit commencer par l'indicatif du Sénégal (221)")
        if len(phone) != 12:
            raise forms.ValidationError("Le numéro doit avoir 12 chiffres (221 + 9 chiffres)")
        return phone

    def clean(self):
        """Validation croisée des mots de passe."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        if password and len(password) < 6:
            raise forms.ValidationError("Le mot de passe doit faire au moins 6 caractères.")

        return cleaned_data

    def save(self, commit=True):
        """Crée automatiquement le compte utilisateur et la boutique."""
        boutique = super().save(commit=False)

        # Créer le compte utilisateur
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        boutique.proprietaire = user

        if commit:
            boutique.save()

        return boutique


class InfobipConfigForm(forms.ModelForm):
    """Formulaire de configuration Infobip pour une boutique existante."""

    class Meta:
        model = Boutique
        fields = ['infobip_display_name']
        widgets = {
            'infobip_display_name': forms.TextInput(attrs={
                'placeholder': 'Ex: SALMON SHOP',
                'class': 'form-control',
                'help_text': 'Nom affiché sur WhatsApp pour vos clients'
            })
        }


class InfobipValidationForm(forms.Form):
    """Formulaire de validation du code SMS Infobip."""

    code = forms.CharField(
        label="Code de validation",
        max_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '123456',
            'class': 'form-control',
            'pattern': '[0-9]{6}',
            'maxlength': '6'
        }),
        help_text="Entrez le code à 6 chiffres reçu par SMS"
    )
