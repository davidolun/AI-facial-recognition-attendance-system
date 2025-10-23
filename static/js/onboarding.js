class OnboardingSystem {
    constructor() {
        this.currentStep = 0;
        this.overlay = null;
        this.isActive = false;
        this.eventHandlers = new Map(); // Better event handler tracking
        this.completedSteps = new Set(); // Track which steps have been completed
        
        // Simplified steps array - focused on actual workflow
        this.steps = [
            {
                title: "Welcome to Smart Attendance! 🎉",
                content: "Let's get you started with your AI-powered attendance system. I'll guide you through each step!",
                target: null,
                action: "welcome",
                page: "any"
            },
            {
                title: "Step 1: Go to Class Management 📚",
                content: "First, let's create a class for your students. Click 'Class Management' in the navigation above.",
                target: ".nav-links a[href='/class_management/']",
                action: "highlight_nav",
                page: "dashboard",
                navigatesTo: "class_management"
            },
            {
                title: "Create Your First Class 🏫",
                content: "Great! Now click the 'Create Class' tab to start creating your first class.",
                target: ".nav-tab[data-tab='create']",
                action: "highlight_button",
                page: "class_management",
                hideOverlayOnClick: true,
                waitForEvent: "classCreated"
            },
            {
                title: "Excellent Work! 🎉",
                content: "You've created your first class! Now let's add a student. Click 'Add Student' in the navigation.",
                target: ".nav-links a[href='/add_student/']",
                action: "highlight_nav",
                page: "class_management",
                navigatesTo: "add_student"
            },
            {
                title: "Add Your First Student 👤",
                content: "Great! Now take a photo of a student and fill in their details to add them to your class.",
                target: "#start, .cam",
                action: "highlight_camera",
                page: "add_student",
                hideOverlayOnShow: true,
                waitForEvent: "studentAdded"
            },
            {
                title: "Now Create a Session 📅",
                content: "Perfect! Now we need to create an attendance session. Click 'Class Management' to go back.",
                target: ".nav-links a[href='/class_management/']",
                action: "highlight_nav",
                page: "add_student",
                navigatesTo: "class_management"
            },
            {
                title: "Click Create Session Tab 📋",
                content: "Now click the 'Create Session' tab and set up your first attendance session.",
                target: ".nav-tab[data-tab='session']",
                action: "highlight_button",
                page: "class_management",
                hideOverlayOnClick: true,
                waitForEvent: "sessionCreated"
            },
            {
                title: "Take Attendance 📷",
                content: "Almost done! Now go to 'Take Attendance' to use the AI camera system.",
                target: ".nav-links a[href='/']",
                action: "highlight_nav",
                page: "class_management",
                navigatesTo: "home"
            },
            {
                title: "Select a Session 📋",
                content: "First, select the session you just created from the dropdown to start taking attendance.",
                target: "#sessionSelect",
                action: "highlight_dropdown",
                page: "home",
                hideOverlayOnClick: true,
                waitForEvent: "sessionSelected"
            },
            {
                title: "Start the Camera 📸",
                content: "Great! Now click 'Start Camera' to begin the face recognition system.",
                target: "#start",
                action: "highlight_button",
                page: "home",
                hideOverlayOnClick: true,
                waitForEvent: "cameraStarted"
            },
            {
                title: "Position Yourself & Take Attendance 👤",
                content: "Keep your face centered in the camera, ensure good lighting, and wait for a GREEN BOX to appear around your face. Click 'Next' to hide this overlay, then click 'Take Attendance' to complete the onboarding!",
                target: null,
                action: "wait_for_action",
                page: "home",
                hideOverlayOnNext: true,
                waitForEvent: "attendanceTaken"
            },
            {
                title: "Success! Attendance Taken! 🎉",
                content: "Excellent! You've successfully taken attendance for {studentName}. The system recognized you and recorded your attendance. You've completed the core workflow!",
                target: null,
                action: "success_message",
                page: "home",
                waitForEvent: "nextStep"
            },
            {
                title: "You're All Set! 🎊",
                content: "Congratulations! You now know the complete workflow. Create classes, add students, create sessions, and take attendance with AI face recognition. Don't forget to explore the 'View Records', 'Advanced Analytics', and 'AI Assistant' pages to get the most out of your system!",
                target: null,
                action: "celebration",
                page: "any"
            }
        ];
        
        this.totalSteps = this.steps.length;
        this.init();
    }

    init() {
        console.log('OnboardingSystem init called');
        
        // Check if user has completed onboarding
        // But allow server-side override for new users
        const isCompleted = localStorage.getItem('onboarding_completed') === 'true';
        const isServerSideStart = window.location.pathname.includes('/dashboard/');
        
        if (isCompleted && !isServerSideStart) {
            console.log('Onboarding already completed');
            return;
        }
        
        if (isCompleted && isServerSideStart) {
            console.log('Server-side onboarding start - clearing localStorage and starting fresh');
            localStorage.removeItem('onboarding_completed');
            localStorage.removeItem('onboarding_step');
            localStorage.removeItem('onboarding_completed_steps');
        }
        
        // Load completed steps from localStorage
        const savedCompletedSteps = localStorage.getItem('onboarding_completed_steps');
        if (savedCompletedSteps) {
            this.completedSteps = new Set(JSON.parse(savedCompletedSteps));
            console.log('Loaded completed steps:', Array.from(this.completedSteps));
        }
        
        // Check if onboarding is in progress
        const savedStep = localStorage.getItem('onboarding_step');
        if (savedStep !== null) {
            this.currentStep = parseInt(savedStep);
            console.log('Resuming onboarding from step:', this.currentStep);
            
            // Mark all previous steps as completed
            for (let i = 0; i < this.currentStep; i++) {
                this.completedSteps.add(i);
            }
            
            // Check current step to see if it's a navigation step that we just completed
            const currentStep = this.steps[this.currentStep];
            const currentPath = window.location.pathname;
            
            // Only auto-advance if this is a "navigation instruction" step and we're now on the target page
            if (currentStep && currentStep.navigatesTo) {
                const targetMatches = this.checkNavigationTarget(currentPath, currentStep.navigatesTo);
                if (targetMatches) {
                    console.log('Auto-advancing due to navigation completion');
                    this.markStepCompleted(this.currentStep);
                    this.currentStep++;
                    localStorage.setItem('onboarding_step', this.currentStep.toString());
                }
            }
        }
        
        // Set up global event listeners BEFORE showing any steps
        this.setupGlobalEventListeners();
        
        // Start onboarding if not completed
        this.startOnboarding();
    }

    checkNavigationTarget(currentPath, navigatesTo) {
        // Check if current path matches the navigation target
        if (navigatesTo === 'class_management' && currentPath.includes('/class_management/')) {
            return true;
        }
        if (navigatesTo === 'add_student' && currentPath.includes('/add_student/')) {
            return true;
        }
        if (navigatesTo === 'home' && (currentPath === '/' || currentPath.includes('/home/'))) {
            return true;
        }
        return false;
    }

    markStepCompleted(stepIndex) {
        console.log('Marking step', stepIndex, 'as completed');
        this.completedSteps.add(stepIndex);
        localStorage.setItem('onboarding_completed_steps', JSON.stringify(Array.from(this.completedSteps)));
    }

    setupGlobalEventListeners() {
        console.log('=== SETTING UP GLOBAL EVENT LISTENERS ===');
        
        // Set up listener for studentAdded event with debouncing
        let studentAddedProcessing = false;
        const studentAddedHandler = (event) => {
            console.log('=== STUDENT ADDED EVENT CAUGHT ===');
            console.log('Event detail:', event.detail);
            console.log('Current step:', this.currentStep);
            console.log('Is active:', this.isActive);
            console.log('Currently processing:', studentAddedProcessing);
            
            // Prevent multiple rapid calls
            if (studentAddedProcessing) {
                console.log('⏭️ Skipping - already processing this event');
                return;
            }
            
            // Check if we're on the correct step (step 4 - Add Your First Student)
            const currentStep = this.steps[this.currentStep];
            console.log('Current step info:', {
                index: this.currentStep,
                title: currentStep?.title,
                waitForEvent: currentStep?.waitForEvent
            });
            
            if (currentStep && currentStep.waitForEvent === 'studentAdded' && this.isActive) {
                console.log('✅ Correct step! Advancing onboarding...');
                studentAddedProcessing = true;
                this.showOverlay();
                setTimeout(() => {
                    this.nextStep();
                    // Reset flag after 2 seconds
                    setTimeout(() => {
                        studentAddedProcessing = false;
                    }, 2000);
                }, 500);
            } else {
                console.log('❌ Not the right step or not active');
                console.log('Current step title:', currentStep?.title);
                console.log('Waiting for event:', currentStep?.waitForEvent);
                console.log('Is active:', this.isActive);
            }
        };
        
        // Only add listener to document (not both document and window)
        document.addEventListener('studentAdded', studentAddedHandler);
        this.eventHandlers.set('studentAdded', studentAddedHandler);
        
        console.log('✅ Global event listeners set up');
        
        // Set up listener for classCreated event with debouncing
        let classCreatedProcessing = false;
        const classCreatedHandler = (event) => {
            console.log('=== CLASS CREATED EVENT CAUGHT ===');
            console.log('Event detail:', event.detail);
            
            if (classCreatedProcessing) {
                console.log('⏭️ Skipping - already processing this event');
                return;
            }
            
            const currentStep = this.steps[this.currentStep];
            if (currentStep && currentStep.waitForEvent === 'classCreated' && this.isActive) {
                console.log('✅ Correct step! Advancing onboarding...');
                classCreatedProcessing = true;
                this.showOverlay();
                setTimeout(() => {
                    this.nextStep();
                    setTimeout(() => {
                        classCreatedProcessing = false;
                    }, 2000);
                }, 500);
            }
        };
        
        document.addEventListener('classCreated', classCreatedHandler);
        this.eventHandlers.set('classCreated', classCreatedHandler);
        
        // Set up listener for sessionCreated event with debouncing
        let sessionCreatedProcessing = false;
        const sessionCreatedHandler = (event) => {
            console.log('=== SESSION CREATED EVENT CAUGHT ===');
            console.log('Event detail:', event.detail);
            
            if (sessionCreatedProcessing) {
                console.log('⏭️ Skipping - already processing this event');
                return;
            }
            
            const currentStep = this.steps[this.currentStep];
            if (currentStep && currentStep.waitForEvent === 'sessionCreated' && this.isActive) {
                console.log('✅ Correct step! Advancing onboarding...');
                sessionCreatedProcessing = true;
                this.showOverlay();
                setTimeout(() => {
                    this.nextStep();
                    setTimeout(() => {
                        sessionCreatedProcessing = false;
                    }, 2000);
                }, 500);
            }
        };
        
        document.addEventListener('sessionCreated', sessionCreatedHandler);
        this.eventHandlers.set('sessionCreated', sessionCreatedHandler);
        
         // Set up listener for sessionSelected event with debouncing
         let sessionSelectedProcessing = false;
         const sessionSelectedHandler = (event) => {
             console.log('=== SESSION SELECTED EVENT CAUGHT ===');
             console.log('Event detail:', event.detail);
             console.log('Event type:', event.type);
             console.log('Event bubbles:', event.bubbles);
             console.log('Current step:', this.currentStep);
             console.log('Current step title:', this.steps[this.currentStep]?.title);
             console.log('Current step waitForEvent:', this.steps[this.currentStep]?.waitForEvent);
             console.log('Is active:', this.isActive);
             console.log('Currently processing:', sessionSelectedProcessing);
             
             if (sessionSelectedProcessing) {
                 console.log('⏭️ Skipping - already processing this event');
                 return;
             }
             
             const currentStep = this.steps[this.currentStep];
             console.log('🔍 Checking step conditions:');
             console.log('- Current step exists:', !!currentStep);
             console.log('- Wait for event matches:', currentStep?.waitForEvent === 'sessionSelected');
             console.log('- Is active:', this.isActive);
             
             if (currentStep && currentStep.waitForEvent === 'sessionSelected' && this.isActive) {
                 console.log('✅ Correct step! Advancing onboarding...');
                 sessionSelectedProcessing = true;
                 this.showOverlay();
                 setTimeout(() => {
                     this.nextStep();
                     setTimeout(() => {
                         sessionSelectedProcessing = false;
                     }, 2000);
                 }, 500);
             } else {
                 console.log('❌ Not the right step or not active');
                 console.log('Current step title:', currentStep?.title);
                 console.log('Waiting for event:', currentStep?.waitForEvent);
                 console.log('Is active:', this.isActive);
             }
         };
        
        document.addEventListener('sessionSelected', sessionSelectedHandler);
        this.eventHandlers.set('sessionSelected', sessionSelectedHandler);
        
        // Set up listener for cameraStarted event with debouncing
        let cameraStartedProcessing = false;
        const cameraStartedHandler = (event) => {
            console.log('=== CAMERA STARTED EVENT CAUGHT ===');
            console.log('Event detail:', event.detail);
            
            if (cameraStartedProcessing) {
                console.log('⏭️ Skipping - already processing this event');
                return;
            }
            
            const currentStep = this.steps[this.currentStep];
            if (currentStep && currentStep.waitForEvent === 'cameraStarted' && this.isActive) {
                console.log('✅ Correct step! Advancing onboarding...');
                cameraStartedProcessing = true;
                this.showOverlay();
                setTimeout(() => {
                    this.nextStep();
                    setTimeout(() => {
                        cameraStartedProcessing = false;
                    }, 2000);
                }, 500);
            }
        };
        
        document.addEventListener('cameraStarted', cameraStartedHandler);
        this.eventHandlers.set('cameraStarted', cameraStartedHandler);
        
        // Set up listener for attendanceTaken event with debouncing
        let attendanceTakenProcessing = false;
        const attendanceTakenHandler = (event) => {
            console.log('=== ATTENDANCE TAKEN EVENT CAUGHT ===');
            console.log('Event detail:', event.detail);
            
            if (attendanceTakenProcessing) {
                console.log('⏭️ Skipping - already processing this event');
                return;
            }
            
            const currentStep = this.steps[this.currentStep];
             if (currentStep && currentStep.waitForEvent === 'attendanceTaken' && this.isActive) {
                 console.log('✅ Correct step! Showing success message...');
                 console.log('Event detail:', event.detail);
                 attendanceTakenProcessing = true;
                 
                 // Extract student name from the event detail
                 let studentName = 'Student';
                 if (event.detail && event.detail.message) {
                     const message = event.detail.message;
                     if (message.includes('Attendance taken:')) {
                         const studentsText = message.replace('Attendance taken: ', '');
                         // Extract just the name (before any status info like "(On time - 10:30:15)")
                         studentName = studentsText.split(' (')[0];
                         if (studentName === 'No match') {
                             studentName = 'Unknown Student';
                         }
                     }
                 }
                 
                 // Store the student name for the success message
                 this.lastRecognizedStudent = studentName;
                 
                 // Mark this step as completed and move to the success message step
                 this.markStepCompleted(this.currentStep);
                 this.currentStep++;
                 
                 // Show overlay with success message
                 this.showOverlay();
                 setTimeout(() => {
                     this.showStep(this.currentStep);
                     setTimeout(() => {
                         attendanceTakenProcessing = false;
                     }, 2000);
                 }, 500);
             }
        };
        
        document.addEventListener('attendanceTaken', attendanceTakenHandler);
        this.eventHandlers.set('attendanceTaken', attendanceTakenHandler);
    }

    shouldAutoAdvance(step) {
        const currentPath = window.location.pathname;
        
        // Step: "Go to Class Management" - advance if we're on class_management page
        if (step.title.includes("Go to Class Management") && currentPath.includes('/class_management/')) {
            return true;
        }
        
        // Step: "Excellent Work! Now let's add a student" - advance if we're on add_student page
        if (step.title.includes("Excellent Work") && currentPath.includes('/add_student/')) {
            return true;
        }
        
        // Step: "Create an Attendance Session" - advance if we're back on class_management
        if (step.title.includes("Create an Attendance Session") && currentPath.includes('/class_management/')) {
            return true;
        }
        
        // Step: "Take Attendance" - advance if we're on home page
        if (step.title.includes("Take Attendance") && (currentPath === '/' || currentPath.includes('/home/'))) {
            return true;
        }
        
        return false;
    }

    startOnboarding() {
        console.log('Starting onboarding...');
        this.isActive = true;
        this.createOverlay();
        this.showStep(this.currentStep);
    }

    createOverlay() {
        console.log('Creating overlay element...');
        
        // Remove any existing overlay first
        const existingOverlay = document.getElementById('onboarding-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.id = 'onboarding-overlay';
        
        this.overlay.innerHTML = `
            <div class="onboarding-modal">
                <div class="onboarding-header">
                    <h2 id="onboarding-title">Welcome!</h2>
                    <button id="onboarding-close" class="onboarding-close">&times;</button>
                </div>
                <div class="onboarding-content">
                    <p id="onboarding-text">Let's get started!</p>
                </div>
                <div class="onboarding-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <span class="progress-text" id="progress-text">Step 1 of ${this.totalSteps}</span>
                </div>
                <div class="onboarding-actions">
                    <button id="onboarding-skip" class="onboarding-btn secondary">Skip Tour</button>
                    <button id="onboarding-prev" class="onboarding-btn secondary" style="display: none;">Previous</button>
                    <button id="onboarding-next" class="onboarding-btn primary">Next</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        this.addStyles();
        this.addEventListeners();
    }

    addStyles() {
        // Remove existing style if present
        const existingStyle = document.getElementById('onboarding-styles');
        if (existingStyle) {
            existingStyle.remove();
        }
        
        const style = document.createElement('style');
        style.id = 'onboarding-styles';
        style.textContent = `
            #onboarding-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                animation: fadeIn 0.3s ease;
                pointer-events: none;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .onboarding-modal {
                background: white;
                border-radius: 16px;
                padding: 2rem;
                max-width: 500px;
                width: 90%;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                pointer-events: auto;
                position: relative;
                animation: slideUp 0.3s ease;
            }

            @keyframes slideUp {
                from { 
                    opacity: 0;
                    transform: translateY(20px);
                }
                to { 
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .onboarding-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }

            .onboarding-header h2 {
                margin: 0;
                color: #1f2937;
                font-size: 1.5rem;
                font-weight: 600;
            }

            .onboarding-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #6b7280;
                padding: 0.25rem;
                border-radius: 4px;
                transition: all 0.2s;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .onboarding-close:hover {
                background: #f3f4f6;
                color: #374151;
            }

            .onboarding-content {
                margin-bottom: 1.5rem;
            }

            .onboarding-content p {
                color: #4b5563;
                line-height: 1.6;
                margin: 0;
                font-size: 1rem;
            }

            .onboarding-progress {
                margin-bottom: 1.5rem;
            }

            .progress-bar {
                width: 100%;
                height: 6px;
                background: #e5e7eb;
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 0.5rem;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #3b82f6, #8b5cf6);
                border-radius: 3px;
                transition: width 0.3s ease;
            }

            .progress-text {
                color: #6b7280;
                font-size: 0.875rem;
                font-weight: 500;
            }

            .onboarding-actions {
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
            }

            .onboarding-btn {
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
                font-size: 0.875rem;
            }

            .onboarding-btn.primary {
                background: #3b82f6;
                color: white;
            }

            .onboarding-btn.primary:hover:not(:disabled) {
                background: #2563eb;
                transform: translateY(-1px);
            }

            .onboarding-btn.secondary {
                background: #f3f4f6;
                color: #374151;
            }

            .onboarding-btn.secondary:hover:not(:disabled) {
                background: #e5e7eb;
            }

            .onboarding-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .onboarding-highlight {
                position: relative;
                z-index: 10001 !important;
                box-shadow: 0 0 0 4px #3b82f6, 0 0 20px rgba(59, 130, 246, 0.5) !important;
                animation: pulse 2s infinite !important;
                border-radius: 8px !important;
                pointer-events: auto !important;
            }

            @keyframes pulse {
                0%, 100% { 
                    box-shadow: 0 0 0 4px #3b82f6, 0 0 20px rgba(59, 130, 246, 0.5);
                }
                50% { 
                    box-shadow: 0 0 0 4px #3b82f6, 0 0 30px rgba(59, 130, 246, 0.8);
                }
            }

            @media (max-width: 600px) {
                .onboarding-modal {
                    padding: 1.5rem;
                    margin: 1rem;
                }
                
                .onboarding-actions {
                    flex-direction: column;
                }
                
                .onboarding-btn {
                    width: 100%;
                }
            }
        `;
        document.head.appendChild(style);
    }

    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) {
            console.warn('Invalid step index:', stepIndex);
            return;
        }

        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];
        
        console.log('=== SHOWING STEP ===');
        console.log('Step Index:', stepIndex);
        console.log('Step Title:', step.title);
        console.log('Wait for event:', step.waitForEvent);
        console.log('Hide overlay on next:', step.hideOverlayOnNext);
        console.log('==================');
        
        // Save current step to localStorage
        localStorage.setItem('onboarding_step', stepIndex.toString());
        
        // Check if we should hide overlay immediately for this step
        if (step.hideOverlayOnShow) {
            console.log('Hiding overlay for user interaction');
            this.hideOverlay();
            // Event listener is already set up globally
            return;
        }
        
        // Check if this is a success message step
        if (step.action === 'success_message') {
            console.log('Showing success message step');
            console.log('Last recognized student:', this.lastRecognizedStudent);
            // Replace placeholder with actual student name
            if (step.content && step.content.includes('{studentName}')) {
                const studentName = this.lastRecognizedStudent || 'Student';
                step.content = step.content.replace('{studentName}', studentName);
            }
        }
        
        // Check if this is a description step
        if (step.action === 'description') {
            console.log('Showing description step');
            // Description steps just show information and wait for next button
        }
        
        // Update modal content
        setTimeout(() => {
            const titleEl = document.getElementById('onboarding-title');
            const textEl = document.getElementById('onboarding-text');
            
            if (titleEl) titleEl.textContent = step.title;
            if (textEl) textEl.textContent = step.content;
            
            // Update progress
            const progress = ((stepIndex + 1) / this.totalSteps) * 100;
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            
            if (progressFill) progressFill.style.width = progress + '%';
            if (progressText) progressText.textContent = `Step ${stepIndex + 1} of ${this.totalSteps}`;
            
            // Update buttons
            const prevBtn = document.getElementById('onboarding-prev');
            const nextBtn = document.getElementById('onboarding-next');
            
            if (prevBtn) prevBtn.style.display = stepIndex === 0 ? 'none' : 'inline-block';
            if (nextBtn) {
                if (stepIndex === this.totalSteps - 1) {
                    nextBtn.textContent = 'Complete';
                } else if (step.action === 'success_message') {
                    nextBtn.textContent = 'Next';
                    nextBtn.style.display = 'inline-block';
                } else {
                    nextBtn.textContent = 'Next';
                }
            }
            
            // Handle highlighting
            this.clearHighlights();
            if (step.target) {
                this.highlightElement(step.target);
                
                if (step.hideOverlayOnClick) {
                    this.setupHideOnClick(step);
                }
            }
        }, 50);
    }

    hideOverlay() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
            console.log('Overlay hidden');
        }
    }

    showOverlay() {
        if (this.overlay) {
            this.overlay.style.display = 'flex';
            console.log('Overlay shown');
        }
    }

    setupHideOnClick(step) {
        console.log('Setting up hide on click for step:', step.title);
        
        const target = document.querySelector(step.target);
        if (!target) {
            console.warn('Target not found for hide on click');
            return;
        }
        
        const clickHandler = () => {
            console.log('Target clicked, hiding overlay');
            this.hideOverlay();
            target.removeEventListener('click', clickHandler);
        };
        
        target.addEventListener('click', clickHandler);
    }

    nextStep() {
        console.log('=== NEXT STEP CALLED ===');
        console.log('Current step before:', this.currentStep);
        console.log('Total steps:', this.totalSteps);
        console.log('Current step title:', this.steps[this.currentStep]?.title);
        
        const currentStep = this.steps[this.currentStep];
        
        // Check if this step should hide overlay on Next button click
        if (currentStep && currentStep.hideOverlayOnNext) {
            console.log('Hiding overlay and waiting for event:', currentStep.waitForEvent);
            this.hideOverlay();
            // Event listener is already set up globally, so just return
            return;
        }
        
        // Mark current step as completed
        this.markStepCompleted(this.currentStep);
        
        console.log('🔍 Checking step bounds:');
        console.log('- Current step:', this.currentStep);
        console.log('- Total steps:', this.totalSteps);
        console.log('- Should continue:', this.currentStep < this.totalSteps - 1);
        
        if (this.currentStep < this.totalSteps - 1) {
            const nextStepIndex = this.currentStep + 1;
            console.log('✅ Moving to step:', nextStepIndex);
            console.log('Next step title:', this.steps[nextStepIndex]?.title);
            this.showStep(nextStepIndex);
        } else {
            console.log('❌ Completing onboarding (last step reached)');
            console.log('Current step was:', this.currentStep);
            console.log('Total steps:', this.totalSteps);
            this.completeOnboarding();
        }
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    completeOnboarding() {
        localStorage.setItem('onboarding_completed', 'true');
        localStorage.removeItem('onboarding_step');
        localStorage.removeItem('onboarding_completed_steps'); // Clear completed steps
        
        // Mark onboarding as completed on the server
        fetch('/mark_onboarding_complete/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            }
        }).then(response => response.json())
        .then(data => {
            console.log('✅ Onboarding marked as complete on server:', data);
        }).catch(error => {
            console.error('❌ Failed to mark onboarding complete on server:', error);
        });
        
        const titleEl = document.getElementById('onboarding-title');
        const textEl = document.getElementById('onboarding-text');
        
        if (titleEl) titleEl.textContent = '🎉 All Done!';
        if (textEl) textEl.textContent = 'You can always restart the tour from your settings. Happy teaching!';
        
        const skipBtn = document.getElementById('onboarding-skip');
        const prevBtn = document.getElementById('onboarding-prev');
        const nextBtn = document.getElementById('onboarding-next');
        
        if (skipBtn) skipBtn.style.display = 'none';
        if (prevBtn) prevBtn.style.display = 'none';
        if (nextBtn) {
            nextBtn.textContent = 'Close';
            nextBtn.onclick = () => this.destroy();
        }
        
        setTimeout(() => {
            this.destroy();
        }, 3000);
    }

    destroy() {
        console.log('=== DESTROYING ONBOARDING ===');
        
        this.clearHighlights();
        
        // Clean up all event handlers
        this.eventHandlers.forEach((handler, eventName) => {
            document.removeEventListener(eventName, handler);
            console.log('Removed event handler:', eventName);
        });
        this.eventHandlers.clear();
        
        if (this.overlay) {
            this.overlay.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                if (this.overlay && this.overlay.parentNode) {
                    this.overlay.remove();
                }
                this.overlay = null;
            }, 300);
        }
        
        this.isActive = false;
        console.log('Onboarding destroyed');
    }

    addEventListeners() {
        const skipBtn = document.getElementById('onboarding-skip');
        const prevBtn = document.getElementById('onboarding-prev');
        const nextBtn = document.getElementById('onboarding-next');
        const closeBtn = document.getElementById('onboarding-close');

        if (skipBtn) skipBtn.onclick = () => this.completeOnboarding();
        if (prevBtn) prevBtn.onclick = () => this.prevStep();
        if (nextBtn) nextBtn.onclick = () => this.nextStep();
        if (closeBtn) closeBtn.onclick = () => this.completeOnboarding();
    }

    clearHighlights() {
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
    }

    highlightElement(selector) {
        try {
            const element = document.querySelector(selector);
            if (element) {
                element.classList.add('onboarding-highlight');
                setTimeout(() => {
                    element.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center',
                        inline: 'center'
                    });
                }, 100);
            } else {
                console.warn('Element not found:', selector);
            }
        } catch (error) {
            console.error('Error highlighting element:', error);
        }
    }
}

// Add fadeOut animation
const fadeOutStyle = document.createElement('style');
fadeOutStyle.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(fadeOutStyle);

// Global functions
window.onboardingSystem = null;

window.startOnboarding = function(clearStorage = true) {
    console.log('startOnboarding called, clearStorage:', clearStorage);
    
    if (clearStorage) {
        localStorage.removeItem('onboarding_completed');
        localStorage.removeItem('onboarding_step');
        localStorage.removeItem('onboarding_completed_steps'); // Clear completed steps tracker
    }
    
    if (window.onboardingSystem) {
        window.onboardingSystem.destroy();
    }
    
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/dashboard/')) {
        console.log('Navigating to dashboard first...');
        localStorage.setItem('start_onboarding_on_load', 'true');
        window.location.href = '/dashboard/';
        return;
    }
    
    setTimeout(() => {
        window.onboardingSystem = new OnboardingSystem();
    }, 100);
};

window.advanceOnboarding = function() {
    if (window.onboardingSystem) {
        window.onboardingSystem.nextStep();
    }
};

window.destroyOnboarding = function() {
    if (window.onboardingSystem) {
        window.onboardingSystem.destroy();
        window.onboardingSystem = null;
    }
};

window.testStudentAddedEvent = function() {
    console.log('🧪 TESTING: Manually dispatching studentAdded event');
    const event = new CustomEvent('studentAdded', {
        detail: { studentName: 'Test Student', studentId: 'TEST123' },
        bubbles: true,
        cancelable: true
    });
    document.dispatchEvent(event);
    window.dispatchEvent(event);
    console.log('🧪 TESTING: studentAdded event dispatched');
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking onboarding...');
    console.log('Current path:', window.location.pathname);
    
    const onboardingCompleted = localStorage.getItem('onboarding_completed');
    const onboardingStep = localStorage.getItem('onboarding_step');
    const shouldStartOnboarding = localStorage.getItem('start_onboarding_on_load');
    
    console.log('Onboarding state:', {
        completed: onboardingCompleted,
        step: onboardingStep,
        shouldStart: shouldStartOnboarding
    });
    
    if (shouldStartOnboarding === 'true') {
        console.log('Starting onboarding after navigation...');
        localStorage.removeItem('start_onboarding_on_load');
        setTimeout(() => {
            window.onboardingSystem = new OnboardingSystem();
        }, 500);
        return;
    }
    
    // Only auto-start onboarding if not on dashboard page (dashboard handles it via server-side flag)
    const currentPath = window.location.pathname;
    if (currentPath.includes('/dashboard/')) {
        console.log('On dashboard page - letting dashboard template handle onboarding');
        return;
    }
    
    if (onboardingCompleted !== 'true') {
        console.log('Starting onboarding...');
        setTimeout(() => {
            window.onboardingSystem = new OnboardingSystem();
        }, 500);
    } else {
        console.log('Onboarding already completed');
    }
});