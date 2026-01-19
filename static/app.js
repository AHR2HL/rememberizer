/**
 * Client-side JavaScript for Rememberizer
 */

// Add keyboard navigation support
document.addEventListener('DOMContentLoaded', function() {
    // Handle number key presses for option selection
    const optionButtons = document.querySelectorAll('.option-button');

    if (optionButtons.length > 0) {
        document.addEventListener('keypress', function(event) {
            const keyNum = parseInt(event.key);
            if (keyNum >= 1 && keyNum <= optionButtons.length) {
                optionButtons[keyNum - 1].click();
            }
        });
    }

    // Add visual feedback for button clicks
    const allButtons = document.querySelectorAll('button, .action-button');
    allButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 100);
        });
    });

    // Add terminal cursor effect to question text
    const questionText = document.querySelector('.question-text');
    if (questionText) {
        const text = questionText.textContent;
        questionText.textContent = '';
        let index = 0;

        function typeWriter() {
            if (index < text.length) {
                questionText.textContent += text.charAt(index);
                index++;
                setTimeout(typeWriter, 20);
            }
        }

        typeWriter();
    }
});
