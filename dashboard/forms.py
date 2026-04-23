"""
Formulaires d'automatisation pour les commerçants Fëgg Jaay.
"""

from django import forms
from django.contrib.auth.models import User
from boutiques.models import Boutique


class CommercantAutoConfigForm(forms.ModelForm):
    """Formulaire simple pour que les commerçants configurent leur WhatsApp Business."""
    
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
    
    accept_terms = forms.BooleanField(
        label="J'accepte les conditions d'utilisation",
        required=True
    )
    
    class Meta:
        model = Boutique
        fields = ['nom', 'telephone_wa', 'proprietaire_tel', 'ville']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Nom de votre boutique'}),
            'telephone_wa': forms.TextInput(attrs={'placeholder': '221771234567'}),
            'proprietaire_tel': forms.TextInput(attrs={'placeholder': '221771234567'}),
            'ville': forms.TextInput(attrs={'placeholder': 'Dakar', 'value': 'Dakar'}),
        }
    
    def clean_telephone_wa(self):
        """Validation du format du numéro WhatsApp."""
        phone = self.cleaned_data['telephone_wa']
        # Nettoyer et valider le format
        phone = phone.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('221'):
            raise forms.ValidationError("Le numéro doit commencer par l'indicatif du Sénégal (221)")
        if len(phone) != 12:
            raise forms.ValidationError("Le numéro doit avoir 12 chiffres (221 + 9 chiffres)")
        return phone
    
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
