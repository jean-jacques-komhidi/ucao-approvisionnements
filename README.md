🎓 UCAO-ISG-CSM — Système de Gestion des Approvisionnements en Ligne



> Projet tutoré  — Master Informatique de Gestion (MIG 1)

> Année académique 2024/2025 — Référence : CG-DFC-CC-01



 📋 Description



Application web de gestion complète du cycle d'approvisionnement à l'UCAO-ISG-CSM,

de la demande (FEB) au paiement, en passant par le bon de commande.



🛠️ Stack technique



\- Backend : Django 4.2 LTS (Python 3.12)

\- Base de données : PostgreSQL 15

\- Templates : Jinja2

\- PDF : WeasyPrint + xhtml2pdf (fallback)

\- Emails : SMTP Gmail

\- Authentification : Django Auth + bcrypt

\- Charts : Chart.js 4.4

\- Icons : Lucide



 ✨ Fonctionnalités implémentées



\- 🔐 Comptes : auth + 8 rôles + blocage 5 tentatives + thème sombre

\- 📦 Référentiels : Articles (avec images) + Services + Fournisseurs (code auto F0001) + Devises

\- 📄 FEB : workflow complet (DRAFT → EN\_INSTANCE → VALIDÉE/CLÔTURÉE/REJETÉE) + lignes dynamiques JS

\- 📋 Bon de Commande : génération automatique si > 50 000 F CFA + PDF + verrouillage

\- 💰 Paiements : circuit DFC → DG → Comptable + paiements partiels (acomptes)

\- 🔔 Notifications : in-app + emails Gmail HTML

\- 📊 Dashboard analytics : KPI adaptatifs par rôle + 4 graphiques Chart.js + alertes intelligentes



 👥 Acteurs



| Rôle | Responsabilités |

|---|---|

| `resp\_appro` | Crée des FEB |

| `chef\_cce` | Crée des FEB |

| `chef\_slmg` | Crée des FEB |

| `cg` | Valide les FEB |

| `dfc` | Valide FEB/BC, ordonne paiements |

| `dg` | Valide BC, vise les paiements |

| `comptable` | Exécute les paiements |

| `admin` | Administration système |



 🚀 Installation



 Prérequis



\- Python 3.12+

\- PostgreSQL 15+

\- Node.js (optionnel, pour outils de build)



 Étapes



```bash

\# 1. Cloner le dépôt

git clone https://github.com/ Jean-Jacques Komhidi/ucao-approvisionnements.git

cd appro\_ucao



\# 2. Créer un environnement virtuel

python -m venv venv

venv\\Scripts\\activate  # Windows

source venv/bin/activate  # Linux/Mac



\# 3. Installer les dépendances

pip install -r requirements.txt



\# 4. Copier .env.example en .env et configurer

copy .env.example .env  # Windows

cp .env.example .env  # Linux/Mac

\# Éditer .env avec tes valeurs



\# 5. Créer la base de données PostgreSQL

\# Connecte-toi à psql et crée la base :

\# CREATE DATABASE appro\_ucao;



\# 6. Migrations

python manage.py migrate



\# 7. Créer un superuser

python manage.py createsuperuser



\# 8. Lancer le serveur

python manage.py runserver

```



📂 Structure du projet



appro\_ucao/

├── apps/

│   ├── comptes/          # Authentification + dashboard

│   ├── referentiels/     # Articles, Services, Fournisseurs, Devises

│   ├── approvisionnements/ # FEB, BC, Paiements

│   └── notifications/    # In-app + emails

├── config/

│   ├── settings/         # base.py, development.py, production.py

│   ├── urls.py

│   └── jinja2\_env.py

├── templates/            # Templates Jinja2

├── static/               # CSS, JS, images

├── media/                # Uploads (images articles)

└── manage.py

## 🎯 Workflow métier

Demandeur crée FEB
        ↓
    EN_INSTANCE
        ↓
    CG / DFC valide
        ↓
   ┌───────────────┐
   ↓               ↓
≤ 50k F        > 50k F
   ↓               ↓
CLÔTURÉE       BC généré (auto)
                    ↓
                 DG valide
                    ↓
             DFC ordonne paiement
                    ↓
                 DG vise
                    ↓
          Comptable exécute paiement
                    ↓
           Email envoyé au fournisseur


## 📊 Captures d'écran

> _(À ajouter)_

## 🏛️ Auteur

**KOMHIDI Jean Jacques**
Master Informatique de Gestion — UCAO-ISG-CSM
2024/2025

## 📜 Master

Projet académique — Tous droits réservés UCAO-ISG-CSM



