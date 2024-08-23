let speech = new SpeechSynthesisUtterance();

document.getElementById('button2').addEventListener('click', function() {
    let answerText = document.getElementById('answer').value;
    speech.text = answerText;
    window.speechSynthesis.speak(speech);
});

// Function to format the text
function formatText(text) {
    // Regular expression to match the pattern and replace it
    const formattedText = text.replace(/^\* \*\*(.*?):\*\* /gm, '$1: ');
    return formattedText;
}

document.getElementById('question-form').addEventListener('submit', async function(event) {
    // Prevent the default form submission behavior
    event.preventDefault();
    
    // Get the question input value
    const question = document.getElementById('question').value;
    if (question) {
        // Hide the response element and clear the answer element
        const responseElement = document.getElementById('response');
        const answerElement = document.getElementById('answer');
        responseElement.style.display = 'none';
        answerElement.textContent = '';

        try {
            // Send the question to the server via a POST request
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });

            // Parse the response data
            const data = await response.json();
            
            // Check if the response is okay, format the text, and display the answer or error message
            if (response.ok) {
                const formattedAnswer = formatText(data.answer);
                answerElement.textContent = formattedAnswer;
            } else {
                answerElement.textContent = data.error || 'An error occurred.';
            }
        } catch (error) {
            // Handle any errors that occurred during the fetch
            answerElement.textContent = 'An error occurred.';
        }

        // Display the response element
        responseElement.style.display = 'block';
    }
});
