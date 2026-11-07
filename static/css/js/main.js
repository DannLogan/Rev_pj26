console.log("🚀 O arquivo main.js foi carregado com sucesso!");

document.addEventListener("DOMContentLoaded", function() {
    
    // ==============================================================================
    // 1. FECHAMENTO AUTOMÁTICO DE ALERTAS (Failsafe Puro)
    // ==============================================================================
    setTimeout(function() {
        const alertas = document.querySelectorAll('.alert:not([data-persistent])');
        alertas.forEach(function(alerta) {
            alerta.style.transition = 'opacity 0.4s ease';
            alerta.style.opacity = '0';
            setTimeout(() => alerta.remove(), 400);
        });
    }, 4000);

    // ==============================================================================
    // 2. FORÇAR FECHAMENTO NO CLIQUE DO "X" (Ignora bugs de Bootstrap)
    // ==============================================================================
    document.querySelectorAll('.alert .btn-close').forEach(function(botaoX) {
        botaoX.addEventListener('click', function() {
            const alertaPai = botaoX.closest('.alert');
            if (alertaPai) {
                alertaPai.style.transition = 'opacity 0.3s ease';
                alertaPai.style.opacity = '0';
                setTimeout(() => alertaPai.remove(), 300);
            }
        });
    });

    // ==============================================================================
    // 3. TRAVA DE CAMPOS DE MATRÍCULA (Apenas Números)
    // ==============================================================================
    const camposMatricula = document.querySelectorAll('input[name="busca_matricula"], input[name="matricula"], #input-matricula');
    camposMatricula.forEach(function(input) {
        if (input.form?.dataset.loginForm !== undefined) return;
        input.setAttribute('inputmode', 'numeric');
        input.setAttribute('pattern', '\\d*');

        input.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '');
        });
    });

});
