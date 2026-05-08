"""
Genere des donnees realistes pour la demo.

Usage :
    python manage.py generer_donnees_demo
    python manage.py generer_donnees_demo --reset  # Reset avant generation
"""
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Genere des donnees demo realistes pour le projet UCAO"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les donnees existantes avant generation",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Reset des donnees..."))
            self._reset_donnees()

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("GENERATION DE DONNEES DEMO UCAO"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        with transaction.atomic():
            utilisateurs = self._creer_utilisateurs()
            devises = self._creer_devises(utilisateurs)
            articles = self._creer_articles(utilisateurs)
            services = self._creer_services(utilisateurs)
            fournisseurs = self._creer_fournisseurs(utilisateurs)
            self._creer_feb_bc_paiements(utilisateurs, articles, services, fournisseurs)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✓ DONNEES DEMO GENEREES AVEC SUCCES !"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self._afficher_recap(utilisateurs)

    # ═══════════════════════════════════════════════════════════════
    # RESET
    # ═══════════════════════════════════════════════════════════════
    def _reset_donnees(self):
        from apps.approvisionnements.models import (
            BonCommande, FicheExpression, LigneFiche,
            OrdrePaiement, Paiement,
        )
        from apps.comptes.models import Utilisateur
        from apps.notifications.models import Notification
        from apps.referentiels.models import Article, Devise, Fournisseur, ServiceExterieur

        Notification.objects.all().delete()
        Paiement.objects.all().delete()
        OrdrePaiement.objects.all().delete()
        LigneFiche.objects.all().delete()
        BonCommande.objects.all().delete()
        FicheExpression.objects.all().delete()
        Article.objects.all().delete()
        ServiceExterieur.objects.all().delete()
        Fournisseur.objects.all().delete()
        Devise.objects.all().delete()
        # On garde l'admin existant
        Utilisateur.objects.exclude(identifiant="admin").delete()

        self.stdout.write(self.style.WARNING("✓ Donnees existantes supprimees"))

    # ═══════════════════════════════════════════════════════════════
    # UTILISATEURS (8 comptes - 1 par role)
    # ═══════════════════════════════════════════════════════════════
    def _creer_utilisateurs(self):
        from apps.comptes.models import RoleUtilisateur, Utilisateur

        users_data = [
            {
                "identifiant": "cathy.sossah",
                "nom_complet": "Cathy Sossah",
                "email": "cathy@gmail.com",
                "role": RoleUtilisateur.RESP_APPRO,
            },
            {
                "identifiant": "moussa.diop",
                "nom_complet": "Moussa Diop",
                "email": "moussa@gmail.com",
                "role": RoleUtilisateur.CHEF_CCE,
            },
            {
                "identifiant": "fatou.fall",
                "nom_complet": "Fatou Fall",
                "email": "fatou@gmail.com",
                "role": RoleUtilisateur.CHEF_SLMG,
            },
            {
                "identifiant": "aminata.kane",
                "nom_complet": "Aminata Kane",
                "email": "aminata@gmail.com",
                "role": RoleUtilisateur.CG,
            },
            {
                "identifiant": "ibrahima.ndiaye",
                "nom_complet": "Ibrahima Ndiaye",
                "email": "ibrahima@gmail.com",
                "role": RoleUtilisateur.DFC,
            },
            {
                "identifiant": "ousmane.sow",
                "nom_complet": "Ousmane Sow",
                "email": "ousmane@gmail.com",
                "role": RoleUtilisateur.DG,
            },
            {
                "identifiant": "marieme.gueye",
                "nom_complet": "Marieme Gueye",
                "email": "marieme@gmail.com",
                "role": RoleUtilisateur.COMPTABLE,
            },
        ]

        users = {}
        # Garde l'admin existant
        try:
            users["admin"] = Utilisateur.objects.get(identifiant="admin")
        except Utilisateur.DoesNotExist:
            pass

        for data in users_data:
            user, created = Utilisateur.objects.get_or_create(
                identifiant=data["identifiant"],
                defaults={
                    "nom_complet": data["nom_complet"],
                    "email": data["email"],
                    "role": data["role"],
                    "est_actif": True,
                },
            )
            if created:
                user.set_password("Test1234!")
                user.save()
                self.stdout.write(f"  ✓ Utilisateur cree : {user.identifiant} ({user.get_role_display()})")
            else:
                self.stdout.write(f"  ↻ Existant : {user.identifiant}")

            users[data["identifiant"]] = user

        return users

    # ═══════════════════════════════════════════════════════════════
    # DEVISES
    # ═══════════════════════════════════════════════════════════════
    def _creer_devises(self, users):
        from apps.referentiels.models import Devise

        admin = users.get("ibrahima.ndiaye")  # DFC

        devises_data = [
            {
                "code": "XOF", "libelle": "Franc CFA BCEAO",
                "symbole": "F", "taux_tva": Decimal("18.00"),
                "est_devise_principale": True, "est_active": True,
            },
            {
                "code": "EUR", "libelle": "Euro",
                "symbole": "€", "taux_tva": Decimal("18.00"),
                "est_devise_principale": False, "est_active": True,
            },
            {
                "code": "USD", "libelle": "Dollar Americain",
                "symbole": "$", "taux_tva": Decimal("18.00"),
                "est_devise_principale": False, "est_active": True,
            },
        ]

        devises = []
        for data in devises_data:
            devise, created = Devise.objects.get_or_create(
                code=data["code"],
                defaults={**data, "gere_par": admin},
            )
            if created:
                self.stdout.write(f"  ✓ Devise creee : {devise.code} ({devise.libelle})")
            devises.append(devise)

        return devises

    # ═══════════════════════════════════════════════════════════════
    # ARTICLES (30 articles realistes)
    # ═══════════════════════════════════════════════════════════════
    def _creer_articles(self, users):
        from apps.referentiels.models import Article

        cathy = users.get("cathy.sossah")

        articles_data = [
            # Bureautique
            {"designation": "Imprimante HP LaserJet Pro M404", "unite": "unite", "nature": "Materiel"},
            {"designation": "Cartouche Toner HP 26A noir", "unite": "unite", "nature": "Consommable"},
            {"designation": "Ordinateur portable Dell Latitude 5520", "unite": "unite", "nature": "Materiel"},
            {"designation": "Ecran LCD 24 pouces Samsung", "unite": "unite", "nature": "Materiel"},
            {"designation": "Clavier USB Logitech K120", "unite": "unite", "nature": "Materiel"},
            {"designation": "Souris optique Logitech B100", "unite": "unite", "nature": "Materiel"},
            {"designation": "Webcam HD 1080p Logitech C920", "unite": "unite", "nature": "Materiel"},

            # Fournitures bureau
            {"designation": "Papier A4 80g (rame de 500)", "unite": "rame", "nature": "Fournitures"},
            {"designation": "Stylo bille bleu Bic", "unite": "boite", "nature": "Fournitures"},
            {"designation": "Cahier 200 pages quadrille", "unite": "unite", "nature": "Fournitures"},
            {"designation": "Classeur a levier A4", "unite": "unite", "nature": "Fournitures"},
            {"designation": "Marqueur permanent noir", "unite": "boite", "nature": "Fournitures"},
            {"designation": "Agrafeuse de bureau", "unite": "unite", "nature": "Fournitures"},
            {"designation": "Boite d'agrafes 24/6", "unite": "boite", "nature": "Fournitures"},
            {"designation": "Trombone metallique 32mm", "unite": "boite", "nature": "Fournitures"},

            # Mobilier
            {"designation": "Chaise de bureau ergonomique", "unite": "unite", "nature": "Mobilier"},
            {"designation": "Bureau en bois 160x80cm", "unite": "unite", "nature": "Mobilier"},
            {"designation": "Armoire metallique 4 etageres", "unite": "unite", "nature": "Mobilier"},
            {"designation": "Tableau blanc magnetique 90x60", "unite": "unite", "nature": "Mobilier"},

            # Reseau / IT
            {"designation": "Cable Ethernet RJ45 Cat6 5m", "unite": "unite", "nature": "Reseau"},
            {"designation": "Switch Cisco 24 ports gigabit", "unite": "unite", "nature": "Reseau"},
            {"designation": "Routeur WiFi TP-Link AC1750", "unite": "unite", "nature": "Reseau"},
            {"designation": "Onduleur APC 1000VA", "unite": "unite", "nature": "Materiel"},

            # Maintenance
            {"designation": "Bombe air comprime 400ml", "unite": "unite", "nature": "Consommable"},
            {"designation": "Lingettes nettoyantes ecrans", "unite": "boite", "nature": "Consommable"},
            {"designation": "Lampe LED 9W E27 (boite de 10)", "unite": "boite", "nature": "Consommable"},

            # Securite
            {"designation": "Extincteur 6kg poudre ABC", "unite": "unite", "nature": "Securite"},
            {"designation": "Cadenas Master Lock 40mm", "unite": "unite", "nature": "Securite"},

            # Alimentation
            {"designation": "Cafe Nestle Nescafe 200g", "unite": "boite", "nature": "Alimentation"},
            {"designation": "Eau minerale Kirene 1.5L (pack 6)", "unite": "pack", "nature": "Alimentation"},
        ]

        articles_crees = []
        for data in articles_data:
            article, created = Article.objects.get_or_create(
                designation=data["designation"],
                defaults={
                    "unite": data["unite"],
                    "nature": data["nature"],
                    "description": f"Article : {data['designation']}",
                    "est_actif": True,
                    "cree_par": cathy,
                },
            )
            if created:
                articles_crees.append(article)

        self.stdout.write(f"  ✓ {len(articles_crees)} articles crees")
        return Article.objects.actifs()

    # ═══════════════════════════════════════════════════════════════
    # SERVICES EXTERIEURS (10 services)
    # ═══════════════════════════════════════════════════════════════
    def _creer_services(self, users):
        from apps.referentiels.models import ServiceExterieur

        cathy = users.get("cathy.sossah")

        services_data = [
            {"designation": "Maintenance climatisation", "description": "Entretien semestriel des climatiseurs"},
            {"designation": "Nettoyage des locaux", "description": "Service de nettoyage hebdomadaire"},
            {"designation": "Reparation imprimante", "description": "Intervention SAV imprimantes"},
            {"designation": "Formation Excel avancee", "description": "Formation 3 jours sur Excel"},
            {"designation": "Audit securite informatique", "description": "Audit annuel cybersecurite"},
            {"designation": "Maintenance reseau", "description": "Maintenance preventive infrastructure"},
            {"designation": "Service de gardiennage", "description": "Gardiennage 24h/24"},
            {"designation": "Transport logistique", "description": "Service de transport de marchandises"},
            {"designation": "Hebergement web", "description": "Hebergement annuel site web"},
            {"designation": "Reparation mobilier", "description": "Reparation mobilier de bureau"},
        ]

        services_crees = []
        for data in services_data:
            service, created = ServiceExterieur.objects.get_or_create(
                designation=data["designation"],
                defaults={
                    "description": data["description"],
                    "est_actif": True,
                    "cree_par": cathy,
                },
            )
            if created:
                services_crees.append(service)

        self.stdout.write(f"  ✓ {len(services_crees)} services crees")
        return ServiceExterieur.objects.actifs()

    # ═══════════════════════════════════════════════════════════════
    # FOURNISSEURS (15 realistes Senegal)
    # ═══════════════════════════════════════════════════════════════
    def _creer_fournisseurs(self, users):
        from apps.referentiels.models import Fournisseur

        cathy = users.get("cathy.sossah")

        fournisseurs_data = [
            {
                "nom": "SARL Bureau Plus Senegal", "type_personne": "morale",
                "telephone": "+221 33 821 45 67", "email": "contact@bureauplus.sn",
                "adresse": "Avenue Lamine Gueye, Plateau, Dakar",
                "ninea": "0001234567890", "rccm": "SN-DKR-2018-B-12345",
            },
            {
                "nom": "Komhidi & Fils", "type_personne": "morale",
                "telephone": "+221 33 824 12 89", "email": "info@komhidi.sn",
                "adresse": "Route de Rufisque, Dakar",
                "ninea": "0002345678901", "rccm": "SN-DKR-2019-B-23456",
            },
            {
                "nom": "Tech Distribution Dakar", "type_personne": "morale",
                "telephone": "+221 33 825 67 45", "email": "vente@techdistrib.sn",
                "adresse": "Sacre Coeur 3, Villa 8521, Dakar",
                "ninea": "0003456789012", "rccm": "SN-DKR-2020-B-34567",
            },
            {
                "nom": "Etablissements Diop Freres", "type_personne": "morale",
                "telephone": "+221 33 869 23 45", "email": "diopfreres@gmail.com",
                "adresse": "Marche Sandaga, Dakar",
                "ninea": "0004567890123", "rccm": "SN-DKR-2017-B-45678",
            },
            {
                "nom": "Wari Services SARL", "type_personne": "morale",
                "telephone": "+221 33 822 78 90", "email": "services@wari.com",
                "adresse": "Mermoz, Avenue Cheikh Anta Diop, Dakar",
                "ninea": "0005678901234", "rccm": "SN-DKR-2015-B-56789",
            },
            {
                "nom": "Alibaba Senegal Import", "type_personne": "morale",
                "telephone": "+221 33 827 34 56", "email": "import@alibabasn.sn",
                "adresse": "Zone industrielle, Dakar",
                "ninea": "0006789012345", "rccm": "SN-DKR-2021-B-67890",
            },
            {
                "nom": "Mamadou Sarr", "type_personne": "physique",
                "telephone": "+221 77 123 45 67", "email": "msarr@yahoo.fr",
                "adresse": "Rufisque, Quartier Diorga",
                "ninea": "", "rccm": "",
            },
            {
                "nom": "Mobilier Senegal SA", "type_personne": "morale",
                "telephone": "+221 33 832 89 01", "email": "ventes@mobiliersn.sn",
                "adresse": "Hann, BP 3214, Dakar",
                "ninea": "0007890123456", "rccm": "SN-DKR-2010-B-78901",
            },
            {
                "nom": "InformaTech Solutions", "type_personne": "morale",
                "telephone": "+221 33 825 90 12", "email": "info@informatech.sn",
                "adresse": "Almadies, Route des Almadies, Dakar",
                "ninea": "0008901234567", "rccm": "SN-DKR-2019-B-89012",
            },
            {
                "nom": "Aissatou Ndiaye Boutique", "type_personne": "physique",
                "telephone": "+221 78 234 56 78", "email": "aissatou.ndiaye@gmail.com",
                "adresse": "Marche HLM, Dakar",
                "ninea": "", "rccm": "",
            },
            {
                "nom": "Senegal Print Services", "type_personne": "morale",
                "telephone": "+221 33 820 67 89", "email": "contact@senegalprint.sn",
                "adresse": "Liberte 6 Extension, Dakar",
                "ninea": "0009012345678", "rccm": "SN-DKR-2018-B-90123",
            },
            {
                "nom": "Ets Babacar Faye", "type_personne": "morale",
                "telephone": "+221 33 821 56 78", "email": "babafaye@gmail.com",
                "adresse": "Pikine, Cite Lobatt, Dakar",
                "ninea": "0001112233445", "rccm": "SN-DKR-2016-B-11223",
            },
            {
                "nom": "Climatisation Express", "type_personne": "morale",
                "telephone": "+221 33 824 33 44", "email": "express@climsn.sn",
                "adresse": "Yoff, Cite Mamelles, Dakar",
                "ninea": "0002233445566", "rccm": "SN-DKR-2020-B-22334",
            },
            {
                "nom": "Senegal Office Supplies", "type_personne": "morale",
                "telephone": "+221 33 823 78 90", "email": "vente@sgloffice.sn",
                "adresse": "Centenaire, Avenue Bourguiba, Dakar",
                "ninea": "0003344556677", "rccm": "SN-DKR-2017-B-33445",
            },
            {
                "nom": "GreenTech Africa", "type_personne": "morale",
                "telephone": "+221 33 829 12 34", "email": "greentech@africa.sn",
                "adresse": "Point E, Dakar",
                "ninea": "0004455667788", "rccm": "SN-DKR-2022-B-44556",
            },
        ]

        fournisseurs_crees = []
        for data in fournisseurs_data:
            # Le code est genere automatiquement par signal
            f, created = Fournisseur.objects.get_or_create(
                nom=data["nom"],
                defaults={**data, "est_actif": True, "cree_par": cathy},
            )
            if created:
                fournisseurs_crees.append(f)

        self.stdout.write(f"  ✓ {len(fournisseurs_crees)} fournisseurs crees")
        return Fournisseur.objects.actifs()

    # ═══════════════════════════════════════════════════════════════
    # FEB + BC + PAIEMENTS (workflow complet)
    # ═══════════════════════════════════════════════════════════════
    def _creer_feb_bc_paiements(self, users, articles, services, fournisseurs):
        from apps.approvisionnements.models import (
            BonCommande, FicheExpression, LigneFiche,
            OrdrePaiement, Paiement,
            StatutBC, StatutFEB, StatutOrdrePaiement, StatutPaiement,
            TypeLigne, ModePaiement, NaturePaiement,
        )
        from apps.approvisionnements.services import (
            calculer_solde_restant, executer_paiement, generer_bc_depuis_feb,
        )

        demandeurs = [
            users.get("cathy.sossah"),
            users.get("moussa.diop"),
            users.get("fatou.fall"),
        ]
        cg = users.get("aminata.kane")
        dfc = users.get("ibrahima.ndiaye")
        dg = users.get("ousmane.sow")
        comptable = users.get("marieme.gueye")

        articles_list = list(articles)
        services_list = list(services)
        fournisseurs_list = list(fournisseurs)

        # ─── 25 FEB sur les 90 derniers jours ─────────────────
        feb_count = 0
        bc_count = 0
        paiement_count = 0

        objets_feb = [
            "Achat fournitures de bureau Q1",
            "Renouvellement parc informatique",
            "Maintenance climatisation",
            "Equipement bureau Direction",
            "Consommables informatiques mensuel",
            "Formation personnel comptabilite",
            "Mobilier salle de reunion",
            "Cartouches imprimantes Q2",
            "Service nettoyage trimestriel",
            "Materiel reseau extension",
            "Reparation extincteurs",
            "Achat papeterie generale",
            "Ordinateurs portables nouveaux recrues",
            "Audit securite informatique annuel",
            "Service gardiennage trimestriel",
            "Lampes LED tous batiments",
            "Pause cafe direction",
            "Cables reseau extension salle 3",
            "Reparation onduleurs salle serveurs",
            "Achat tablettes presentations",
            "Service hebergement web annuel",
            "Maintenance reseau preventive",
            "Mobilier bureau accueil",
            "Materiel pedagogique",
            "Equipement salle informatique",
        ]

        for i in range(25):
            # Date aleatoire dans les 90 derniers jours
            jours_avant = random.randint(1, 90)
            date_creation = timezone.now() - timedelta(days=jours_avant)

            demandeur = random.choice(demandeurs)
            fournisseur = random.choice(fournisseurs_list)
            objet = objets_feb[i] if i < len(objets_feb) else f"Demande #{i+1}"

            # Cree FEB en mode "manuel" pour eviter le signal
            feb = FicheExpression(
                demandeur=demandeur,
                fournisseur=fournisseur,
                objet=objet,
                statut=StatutFEB.DRAFT,  # On change apres
                taux_tva=Decimal("18.00"),
                date_creation=date_creation,
            )
            feb.save()

            # Force la date de creation (auto_now_add la sur-ecrit)
            FicheExpression.objects.filter(pk=feb.pk).update(
                date_creation=date_creation
            )
            feb.refresh_from_db()

            # ─── Lignes : 2 a 5 lignes par FEB ────────────────
            nb_lignes = random.randint(2, 5)
            total_ht = Decimal("0.00")

            for _ in range(nb_lignes):
                # 70% Article, 30% Service
                if random.random() < 0.7:
                    article = random.choice(articles_list)
                    service = None
                    type_ligne = TypeLigne.ARTICLE
                else:
                    article = None
                    service = random.choice(services_list)
                    type_ligne = TypeLigne.SERVICE

                quantite = Decimal(str(random.randint(1, 20)))
                prix_unitaire = Decimal(str(random.choice([
                    5000, 12000, 25000, 35000, 50000, 75000, 100000,
                    125000, 150000, 200000, 250000, 350000, 500000,
                ])))

                ligne = LigneFiche.objects.create(
                    fiche=feb,
                    type_ligne=type_ligne,
                    article=article,
                    service=service,
                    designation_libre="",
                    quantite=quantite,
                    prix_unitaire=prix_unitaire,
                )
                total_ht += ligne.montant_ligne

            # Calcul totaux
            feb.calculer_totaux()
            feb.refresh_from_db()

            # ─── Determine statut final selon la logique metier ────
            # 80% des FEB sont validees, 10% rejetees, 10% en instance
            r = random.random()

            if r < 0.7:  # 70% validees
                feb.statut = StatutFEB.EN_INSTANCE  # On passe d'abord par EN_INSTANCE
                feb.save()

                # Puis valide
                date_validation = date_creation + timedelta(days=random.randint(1, 5))

                if feb.est_au_dela_du_seuil:
                    feb.statut = StatutFEB.VALIDEE
                else:
                    feb.statut = StatutFEB.CLOTUREE

                feb.validateur = cg if random.random() < 0.5 else dfc
                feb.date_validation = date_validation
                feb.save()

                # Si > 50k → Genere BC
                if feb.est_au_dela_du_seuil:
                    bc = generer_bc_depuis_feb(feb)
                    bc_count += 1

                    # 70% des BC sont valides
                    if random.random() < 0.7:
                        bc.statut = StatutBC.VALIDE
                        bc.validateur = dg
                        bc.date_validation = date_validation + timedelta(days=1)
                        bc.save()

                        # 60% des BC valides ont un paiement
                        if random.random() < 0.6:
                            self._creer_paiement_pour_bc(
                                bc, dfc, dg, comptable,
                                date_creation_bc=date_validation,
                            )
                            paiement_count += 1

            elif r < 0.85:  # 15% en instance
                feb.statut = StatutFEB.EN_INSTANCE
                feb.save()

            else:  # 15% rejetees
                feb.statut = StatutFEB.EN_INSTANCE
                feb.save()
                feb.statut = StatutFEB.REJETEE
                feb.validateur = cg
                feb.motif_action = random.choice([
                    "Budget insuffisant pour cette demande",
                    "Necessite revision avec direction",
                    "Fournisseur non agree",
                    "Documents justificatifs manquants",
                    "Hors politique d'approvisionnement",
                ])
                feb.save()

            feb_count += 1

        self.stdout.write(f"  ✓ {feb_count} FEB creees")
        self.stdout.write(f"  ✓ {bc_count} BC generes")
        self.stdout.write(f"  ✓ {paiement_count} paiements executes")

    def _creer_paiement_pour_bc(self, bc, dfc, dg, comptable, date_creation_bc):
        """Cree un cycle complet : OrdrePaiement -> Visa DG -> Paiement."""
        from apps.approvisionnements.models import (
            ModePaiement, NaturePaiement, OrdrePaiement, Paiement,
            StatutOrdrePaiement, StatutPaiement,
        )
        from apps.approvisionnements.services import executer_paiement

        modes = [ModePaiement.VIREMENT, ModePaiement.CHEQUE, ModePaiement.MOBILE_MONEY]

        # Cree ordre
        date_ordre = date_creation_bc + timedelta(days=random.randint(1, 3))
        ordre = OrdrePaiement.objects.create(
            bc=bc,
            dfc=dfc,
            montant=bc.montant_ttc,
            nature=NaturePaiement.INTEGRAL,
            mode=random.choice(modes),
            statut=StatutOrdrePaiement.VISA_OK,
            dg=dg,
            date_visa=date_ordre + timedelta(days=1),
        )

        # Cree paiement
        date_paiement = date_ordre + timedelta(days=random.randint(2, 5))
        paiement = Paiement(
            bc=bc,
            ordre=ordre,
            comptable=comptable,
            montant_verse=bc.montant_ttc,
            nature=NaturePaiement.INTEGRAL,
            mode=ordre.mode,
            reference=f"REF-{random.randint(100000, 999999)}",
        )
        paiement.save()

        # Execute (calcule le statut + solde)
        executer_paiement(paiement)

    # ═══════════════════════════════════════════════════════════════
    # RECAP
    # ═══════════════════════════════════════════════════════════════
    def _afficher_recap(self, users):
        self.stdout.write("\n" + self.style.SUCCESS("UTILISATEURS DE TEST :"))
        self.stdout.write(self.style.SUCCESS("-" * 60))
        self.stdout.write("Mot de passe pour tous : Test1234!\n")

        self.stdout.write(f"  • {'admin':20} (Admin Systeme)")
        for ident, user in users.items():
            if ident == "admin":
                continue
            self.stdout.write(f"  • {user.identifiant:20} ({user.get_role_display()})")

        self.stdout.write("\n" + self.style.SUCCESS("PROCHAINES ETAPES :"))
        self.stdout.write("  1. Lancer le serveur : python manage.py runserver")
        self.stdout.write("  2. Aller sur : http://127.0.0.1:8000/")
        self.stdout.write("  3. Tester les differents roles avec Test1234!")
        self.stdout.write("  4. Le dashboard devrait etre rempli de donnees realistes")