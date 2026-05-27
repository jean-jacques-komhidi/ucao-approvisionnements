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

<img width="1910" height="958" alt="Capture d&#39;écran 2026-05-27 212731" src="https://github.com/user-attachments/assets/fbbec019-30f1-48bd-8fd7-0eab31beac98" />
<img width="1913" height="954" alt="Capture d&#39;écran 2026-05-27 211611" src="https://github.com/user-attachments/assets/3286c044-0667-4f3b-9676-f85697cd72ee" />
<img width="1916" height="955" alt="Capture d&#39;écran 2026-05-27 211643" src="https://github.com/user-attachments/assets/54a42eef-bf2b-440f-ae84-f891d193f7c2" />
<img width="1911" height="953" alt="Capture d&#39;écran 2026-05-27 211710" src="https://github.com/user-attachments/assets/1fec99a3-8c91-416c-bba0-e7d8fb72e49d" />
<img width="1917" height="951" alt="Capture d&#39;écran 2026-05-27 211729" src="https://github.com/user-attachments/assets/882b775f-970a-45b1-a4bd-8cd21815af94" />
<img width="1915" height="961" alt="Capture d&#39;écran 2026-05-27 211802" src="https://github.com/user-attachments/assets/f6728871-79ca-4ea8-9cc7-e138c75c08ab" />
<img width="1919" height="964" alt="Capture d&#39;écran 2026-05-27 211819" src="https://github.com/user-attachments/assets/dae17529-a0fc-42b3-9c7c-aad2c81c6837" />
<img width="1918" height="953" alt="Capture d&#39;écran 2026-05-27 211944" src="https://github.com/user-attachments/assets/9e5b9c03-99df-4ecd-ba7c-cc2536d1cc01" />
<img width="1913" height="954" alt="Capture d&#39;écran 2026-05-27 212002" src="https://github.com/user-attachments/assets/f88a3a57-a5dd-44e5-9f88-228c44fe1dfa" />
<img width="1913" height="959" alt="Capture d&#39;écran 2026-05-27 212031" src="https://github.com/user-attachments/assets/ca7cf269-5c7e-4005-980e-1b00e4958ccb" />
<img width="1913" height="961" alt="Capture d&#39;écran 2026-05-27 212045" src="https://github.com/user-attachments/assets/a0240cd9-0b31-4047-8b52-e0b167ca8ee3" />
<img width="1919" height="958" alt="Capture d&#39;écran 2026-05-27 212124" src="https://github.com/user-attachments/assets/33119419-cd11-442f-8b80-b37744aa30cc" />
<img width="1909" height="966" alt="Capture d&#39;écran 2026-05-27 212147" src="https://github.com/user-attachments/assets/b3c671c1-7d6a-4afa-9c11-5ddbaa5558a6" />
<img width="1906" height="959" alt="Capture d&#39;écran 2026-05-27 212521" src="https://github.com/user-attachments/assets/c2459103-4d4e-405e-a765-07a41844ebc1" />
<img width="1910" height="959" alt="Capture d&#39;écran 2026-05-27 212540" src="https://github.com/user-attachments/assets/77406a68-4de4-4c07-b04b-45c21cdb9528" />
<img width="1916" height="960" alt="Capture d&#39;écran 2026-05-27 212603" src="https://github.com/user-attachments/assets/6612a513-a18b-4edc-a2e1-842fae3ca0d7" />
<img width="1916" height="958" alt="Capture d&#39;écran 2026-05-27 212653" src="https://github.com/user-attachments/assets/a32fa55e-3cd8-48c4-b290-de5e51e7141c" />
<img width="1910" height="958" alt="Capture d&#39;écran 2026-05-27 212731" src="https://github.com/user-attachments/assets/9f79e622-9a48-4877-96e5-31d9e98694b5" />


## 🏛️ Auteur

**KOMHIDI Jean Jacques**
Master Informatique de Gestion — UCAO-ISG-CSM
2024/2025

## 📜 Master

Projet académique — Tous droits réservés UCAO-ISG-CSM



