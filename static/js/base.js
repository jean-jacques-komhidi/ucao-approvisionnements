/**
 * UCAO Approvisionnements - Script de base
 *
 * - Toggle entre mode clair et sombre (sauvegarde localStorage)
 * - Initialisation des icones Lucide
 */
(function() {
    'use strict';

    const racineHtml = document.documentElement;
    const cleStockage = 'theme';

    /**
     * Applique un theme et le sauvegarde.
     */
    function appliquerTheme(theme) {
        racineHtml.setAttribute('data-theme', theme);
        localStorage.setItem(cleStockage, theme);
    }

    /**
     * Bascule entre clair et sombre.
     */
    function basculerTheme() {
        const themeActuel = racineHtml.getAttribute('data-theme') || 'light';
        const nouveauTheme = themeActuel === 'light' ? 'dark' : 'light';
        appliquerTheme(nouveauTheme);

        // Re-initialise Lucide pour mettre a jour les icones
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Initialise toutes les icones Lucide presentes dans la page.
     */
    function initialiserIcones() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Initialise les ecouteurs d'evenements.
     */
    function initialiser() {
        // Initialise les icones
        initialiserIcones();

        // Toggle theme
        const boutonTheme = document.getElementById('btn-theme');
        if (boutonTheme) {
            boutonTheme.addEventListener('click', basculerTheme);
        }

        // Detecte le theme prefere du systeme si rien n'est sauvegarde
        if (!localStorage.getItem(cleStockage)) {
            const prefereSystemSombre = window.matchMedia('(prefers-color-scheme: dark)').matches;
            appliquerTheme(prefereSystemSombre ? 'dark' : 'light');
        }
    }

    // Lancement quand le DOM est pret
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialiser);
    } else {
        initialiser();
    }

})();