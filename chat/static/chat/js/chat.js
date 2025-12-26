document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const chatToggle = document.getElementById('chat-toggle');
    const chatContainer = document.getElementById('chat-container');
    const closeChat = document.getElementById('close-chat');
    const expandChat = document.getElementById('expand-chat');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // State
    let isExpanded = false;
    
    // Initialize chat
    function initChat() {
        // Start with chat closed (no auto-show)
        chatContainer.classList.add('opacity-0', 'invisible', 'translate-y-4');
    }
    
    // Toggle chat visibility
    function toggleChat(e) {
        e.stopPropagation(); // Prevent event from bubbling up
        
        if (chatContainer.classList.contains('opacity-0')) {
            // Open chat
            chatContainer.classList.remove('invisible');
            // Force reflow to ensure the transition works
            void chatContainer.offsetWidth;
            chatContainer.classList.remove('opacity-0', 'translate-y-4');
            chatContainer.classList.add('opacity-100', 'translate-y-0');
            userInput.focus();
        } else {
            // Close chat
            chatContainer.classList.remove('opacity-100', 'translate-y-0');
            chatContainer.classList.add('opacity-0', 'translate-y-4');
            // Hide after animation completes
            setTimeout(() => {
                chatContainer.classList.add('invisible');
            }, 300);
        }
    }
    
    // Toggle chat between expanded and normal size
    function toggleExpand() {
        isExpanded = !isExpanded;
        if (isExpanded) {
            // For expanded view, set a max height based on viewport height
            chatContainer.style.maxHeight = '90vh';
            chatContainer.style.top = '5vh';
            chatContainer.style.bottom = 'auto';
            chatContainer.classList.add('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            chatContainer.classList.remove('w-96', 'right-8');
            expandChat.innerHTML = '<i class="fas fa-compress text-sm"></i>';
        } else {
            // For normal view, reset to default positioning
            chatContainer.style.maxHeight = '80vh';
            chatContainer.style.top = '';
            chatContainer.style.bottom = '7rem';
            chatContainer.classList.remove('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            chatContainer.classList.add('w-96', 'right-8');
            expandChat.innerHTML = '<i class="fas fa-expand text-sm"></i>';
        }
        // Ensure messages scroll to bottom after resize
        scrollToBottom();
    }
    
    // Set up event listeners
    function setupEventListeners() {
        // Toggle chat window
        chatToggle.addEventListener('click', toggleChat);
        
        // Close chat window
        closeChat.addEventListener('click', toggleChat);
        
        // Toggle expand/collapse
        expandChat.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleExpand();
        });
        
        // Close chat when clicking outside
        document.addEventListener('click', function(e) {
            if (!chatContainer.contains(e.target) && e.target !== chatToggle) {
                if (!chatContainer.classList.contains('opacity-0')) {
                    toggleChat(e);
                }
            }
        });
        
        // Handle form submission
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendMessage();
        });
        
        // Send message on button click
        sendButton.addEventListener('click', function() {
            sendMessage();
        });
        
        // Send message on Enter key (but allow Shift+Enter for new line)
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth < 768) { // Mobile view
                chatContainer.classList.remove('w-96', 'w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
                chatContainer.classList.add('w-[calc(100%-2rem)]', 'right-4');
            } else if (isExpanded) {
                chatContainer.classList.remove('w-96', 'w-[calc(100%-2rem)]', 'right-4');
                chatContainer.classList.add('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            } else {
                chatContainer.classList.remove('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2', 'w-[calc(100%-2rem)]', 'right-4');
                chatContainer.classList.add('w-96', 'right-8');
            }
        });
    }
    
    // Load chat history
    function loadChatHistory() {
        fetch('/chat/send/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.chats && data.chats.length > 0) {
                data.chats.forEach(chat => {
                    addMessage(chat.user_message, 'user');
                    addMessage(chat.ai_message, 'ai');
                });
                scrollToBottom();
            }
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
        });
    }
    
    // Function to send a message
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        
        // Show loading state
        setLoadingState(true);
        
        // Scroll to bottom
        scrollToBottom();
        
        // Send message to server
        fetch('/chat/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message
            }),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addMessage(data.ai_message, 'ai');
            } else {
                addMessage('Sorry, there was an error processing your request.', 'ai');
                console.error('Error:', data.error);
            }
            setLoadingState(false);
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('Sorry, there was an error connecting to the server.', 'ai');
            setLoadingState(false);
            scrollToBottom();
        });
    }
    
    // Function to format message with links and basic markdown
    function formatMessage(message) {
        // Escape HTML first to prevent XSS
        let formatted = message
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Convert markdown-style links [text](url) to HTML links
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(match, text, url) {
            return '<a href="' + url + '" class="text-teal-400 hover:text-teal-300 underline font-medium">' + text + '</a>';
        });
        
        // Convert newlines to <br>
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Convert emoji arrows 👉 to styled spans
        formatted = formatted.replace(/👉/g, '<span class="mr-1">👉</span>');
        
        return formatted;
    }
    
    // Function to add a message to the chat
    function addMessage(message, sender) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `max-w-[80%] px-4 py-3 rounded-lg shadow ${
            sender === 'user' 
                ? 'bg-gradient-to-r from-blue-600 to-teal-600 text-white rounded-br-none' 
                : 'bg-gray-700 text-gray-100 rounded-bl-none'
        }`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (sender === 'user') {
            // User messages are plain text (no need to parse links)
            messageContent.textContent = message;
        } else {
            // AI messages may contain links - render as HTML
            messageContent.innerHTML = formatMessage(message);
        }
        
        const messageMeta = document.createElement('div');
        messageMeta.className = 'text-xs text-gray-300 mt-1 text-right';
        messageMeta.textContent = sender === 'user' ? 'You • Just now' : 'TSC Assistant • Just now';
        
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageMeta);
        messageContainer.appendChild(messageDiv);
        
        chatMessages.appendChild(messageContainer);
        scrollToBottom();
    }
    
    // Set loading state
    function setLoadingState(loading) {
        if (loading) {
            sendButton.disabled = true;
            userInput.disabled = true;
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            typingIndicator.classList.remove('hidden');
        } else {
            sendButton.disabled = false;
            userInput.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            typingIndicator.classList.add('hidden');
            userInput.focus();
        }
    }
    
    // Scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initialize the chat
    initChat();
    setupEventListeners();
    loadChatHistory();
});
