// Lisa Care Companion Dashboard JavaScript

class Dashboard {
    constructor() {
        this.patients = [];
        this.currentPatient = null;
        this.charts = {}; // Store chart instances
        this.init();
    }

    async init() {
        await this.loadDashboardStats();
        await this.loadPatients();
    }

    showLoading() {
        document.getElementById('loading').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }

    async loadDashboardStats() {
        try {
            const response = await fetch('/api/dashboard/stats');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('total-patients').textContent = data.stats.totalPatients;
                document.getElementById('total-visits').textContent = data.stats.totalVisits;
                document.getElementById('recent-visits').textContent = data.stats.recentVisits;
                document.getElementById('needs-followup').textContent = data.stats.needsFollowUp;
            }
        } catch (error) {
            console.error('Error loading dashboard stats:', error);
        }
    }

    async loadPatients() {
        this.showLoading();
        try {
            const response = await fetch('/api/patients');
            const data = await response.json();
            
            if (data.success) {
                this.patients = data.patients;
                this.renderPatients();
            } else {
                console.error('Error loading patients:', data.error);
            }
        } catch (error) {
            console.error('Error loading patients:', error);
        } finally {
            this.hideLoading();
        }
    }

    renderPatients() {
        const container = document.getElementById('patients-container');
        container.innerHTML = '';

        this.patients.forEach(patient => {
            const patientCard = this.createPatientCard(patient);
            container.appendChild(patientCard);
        });
    }

    createPatientCard(patient) {
        const col = document.createElement('div');
        col.className = 'col-lg-4 col-md-6 col-sm-12 mb-4 fade-in';
        
        const conditions = patient.conditions || [];
        const conditionNames = conditions.map(c => c.name).join(', ');
        
        col.innerHTML = `
            <div class="card patient-card">
                <div class="card-body text-center">
                    <div class="patient-avatar">
                        ${patient.preferredName ? patient.preferredName.charAt(0).toUpperCase() : 'P'}
                    </div>
                    <h5 class="patient-name">${patient.preferredName || patient.firstName || 'Unknown'}</h5>
                    <div class="patient-details">
                        <div><i class="fas fa-user me-1"></i> ${patient.age || 'N/A'} years old</div>
                        <div><i class="fas fa-venus-mars me-1"></i> ${patient.gender || 'N/A'}</div>
                        <div><i class="fas fa-stethoscope me-1"></i> ${conditionNames || 'No conditions'}</div>
                    </div>
                    <div class="patient-actions">
                        <button class="btn btn-primary btn-action" onclick="dashboard.viewVisits('${patient._id}', '${patient.preferredName || patient.firstName}')">
                            <i class="fas fa-phone me-1"></i> View Visits
                        </button>
                        <button class="btn btn-outline-primary btn-action" onclick="dashboard.viewProfile('${patient._id}')">
                            <i class="fas fa-user me-1"></i> Profile
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return col;
    }

    async viewVisits(patientId, patientName) {
        this.showLoading();
        try {
            const response = await fetch(`/api/patients/${patientId}/visits`);
            const data = await response.json();
            
            if (data.success) {
                this.renderVisits(data.visits, patientName);
                const modal = new bootstrap.Modal(document.getElementById('visitsModal'));
                modal.show();
            } else {
                console.error('Error loading visits:', data.error);
            }
        } catch (error) {
            console.error('Error loading visits:', error);
        } finally {
            this.hideLoading();
        }
    }

    renderVisits(visits, patientName) {
        const container = document.getElementById('visits-container');
        const analyticsSection = document.getElementById('analytics-section');
        
        if (visits.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-phone-slash fa-3x text-muted mb-3"></i>
                    <h5>No visits yet</h5>
                    <p class="text-muted">No care calls have been made to ${patientName} yet.</p>
                </div>
            `;
            analyticsSection.style.display = 'none';
            return;
        }

        // Show analytics first if there are multiple visits
        if (visits.length > 1) {
            analyticsSection.style.display = 'block';
            this.createAnalyticsCharts(visits);
        } else {
            analyticsSection.style.display = 'none';
        }

        // Then render the visits list
        container.innerHTML = `
            <h6 class="mb-3">Care Calls for ${patientName}</h6>
            ${visits.map(visit => this.createVisitCard(visit)).join('')}
        `;
    }

    createVisitCard(visit) {
        const date = new Date(visit.timestamp).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        const summary = visit.summary || {};
        const analysis = visit.openaiAnalysis || {};
        
        const highlights = this.createHighlights(summary, analysis);
        const details = this.createVisitDetails(visit);

        return `
            <div class="visit-card">
                <div class="visit-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">Care Call</h6>
                            <div class="visit-date">${date}</div>
                        </div>
                        <div>
                            <span class="status-indicator ${this.getStatusClass(summary.mood)}"></span>
                            ${summary.mood || 'Unknown'}
                        </div>
                    </div>
                </div>
                
                <div class="visit-highlights">
                    <h6 class="mb-3"><i class="fas fa-star me-2"></i>Highlights</h6>
                    ${highlights}
                </div>
                
                <div class="visit-details" style="display: none;">
                    ${details}
                </div>
                
                <div class="card-footer bg-light">
                    <button class="btn btn-sm btn-outline-primary" onclick="dashboard.toggleVisitDetails(this)">
                        <i class="fas fa-chevron-down me-1"></i> Show Details
                    </button>
                </div>
            </div>
        `;
    }

    createHighlights(summary, analysis) {
        const highlights = [];
        
        // Medication status
        const medStatus = summary.medicationsTaken ? 'Taken' : 'Missed';
        const medIcon = summary.medicationsTaken ? 'fa-check-circle' : 'fa-exclamation-triangle';
        const medColor = summary.medicationsTaken ? 'bg-success' : 'bg-warning';
        highlights.push(`
            <div class="highlight-item">
                <div class="highlight-icon ${medColor}">
                    <i class="fas ${medIcon}"></i>
                </div>
                <div class="highlight-text">
                    <strong>Medication:</strong> ${medStatus}
                </div>
            </div>
        `);

        // Pain level
        if (summary.painReport !== undefined) {
            const painIcon = summary.painReport > 5 ? 'fa-exclamation-triangle' : 'fa-smile';
            const painColor = summary.painReport > 5 ? 'bg-warning' : 'bg-success';
            highlights.push(`
                <div class="highlight-item">
                    <div class="highlight-icon ${painColor}">
                        <i class="fas ${painIcon}"></i>
                    </div>
                    <div class="highlight-text">
                        <strong>Pain Level:</strong> ${summary.painReport}/10
                    </div>
                </div>
            `);
        }

        // Food intake
        if (summary.foodIntake) {
            const foodIcon = summary.foodIntake === 'normal' ? 'fa-utensils' : 'fa-exclamation-circle';
            const foodColor = summary.foodIntake === 'normal' ? 'bg-success' : 'bg-warning';
            highlights.push(`
                <div class="highlight-item">
                    <div class="highlight-icon ${foodColor}">
                        <i class="fas ${foodIcon}"></i>
                    </div>
                    <div class="highlight-text">
                        <strong>Food Intake:</strong> ${summary.foodIntake}
                    </div>
                </div>
            `);
        }

        // Sleep quality
        if (summary.sleepQuality) {
            const sleepIcon = summary.sleepQuality === 'good' ? 'fa-bed' : 'fa-exclamation-circle';
            const sleepColor = summary.sleepQuality === 'good' ? 'bg-success' : 'bg-warning';
            highlights.push(`
                <div class="highlight-item">
                    <div class="highlight-icon ${sleepColor}">
                        <i class="fas ${sleepIcon}"></i>
                    </div>
                    <div class="highlight-text">
                        <strong>Sleep Quality:</strong> ${summary.sleepQuality}
                    </div>
                </div>
            `);
        }

        // Hospitalization Risk
        const hospitalizationPred = analysis.hospitalizationPrediction;
        if (hospitalizationPred && hospitalizationPred.riskLevel) {
            const riskLevel = hospitalizationPred.riskLevel;
            const confidence = hospitalizationPred.confidence || 0;
            const riskIcon = riskLevel === 'HIGH' ? 'fa-exclamation-triangle' : 'fa-shield-alt';
            const riskColor = riskLevel === 'HIGH' ? 'bg-danger' : 'bg-success';
            highlights.push(`
                <div class="highlight-item">
                    <div class="highlight-icon ${riskColor}">
                        <i class="fas ${riskIcon}"></i>
                    </div>
                    <div class="highlight-text">
                        <strong>Hospitalization Risk:</strong> ${riskLevel} (${(confidence * 100).toFixed(0)}%)
                    </div>
                </div>
            `);
        }

        // Key insights from OpenAI analysis
        if (analysis.keyInsights && analysis.keyInsights.length > 0) {
            analysis.keyInsights.slice(0, 2).forEach(insight => {
                highlights.push(`
                    <div class="highlight-item">
                        <div class="highlight-icon bg-info">
                            <i class="fas fa-lightbulb"></i>
                        </div>
                        <div class="highlight-text">
                            <strong>Insight:</strong> ${insight}
                        </div>
                    </div>
                `);
            });
        }

        return highlights.join('');
    }

    createVisitDetails(visit) {
        const summary = visit.summary || {};
        const analysis = visit.openaiAnalysis || {};
        
        return `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="mb-3"><i class="fas fa-clipboard-list me-2"></i>Health Summary</h6>
                    <div class="detail-row">
                        <span class="detail-label">Medications Taken:</span>
                        <span class="detail-value">${summary.medicationsTaken ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Pain Report:</span>
                        <span class="detail-value">${summary.painReport || 'N/A'}/10</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Memory Issues:</span>
                        <span class="detail-value">${summary.memoryIssuesNoted ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Able to Leave House:</span>
                        <span class="detail-value">${summary.ableToLeaveHouse ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Small Talk Topic:</span>
                        <span class="detail-value">${summary.smallTalkTopic || 'N/A'}</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="mb-3"><i class="fas fa-brain me-2"></i>AI Analysis</h6>
                    ${this.createAnalysisDetails(analysis)}
                </div>
            </div>
        `;
    }

    createAnalysisDetails(analysis) {
        if (!analysis || Object.keys(analysis).length === 0) {
            return '<p class="text-muted">No AI analysis available</p>';
        }

        let details = '';
        
        if (analysis.conversationContext) {
            const context = analysis.conversationContext;
            details += `
                <div class="detail-row">
                    <span class="detail-label">Enthusiasm Level:</span>
                    <span class="detail-value">${context.enthusiasmLevel || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Topic Interest:</span>
                    <span class="detail-value">${context.topicInterest || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Conversation Flow:</span>
                    <span class="detail-value">${context.conversationFlow || 'N/A'}</span>
                </div>
            `;
        }

        if (analysis.recommendations && analysis.recommendations.length > 0) {
            details += `
                <div class="mt-3">
                    <strong>Recommendations:</strong>
                    <ul class="mt-2">
                        ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        if (analysis.riskFactors && analysis.riskFactors.length > 0) {
            details += `
                <div class="mt-3">
                    <strong>Risk Factors:</strong>
                    <ul class="mt-2">
                        ${analysis.riskFactors.map(risk => `<li class="text-warning">${risk}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        return details;
    }

    getStatusClass(mood) {
        switch (mood) {
            case 'cheerful':
            case 'happy':
                return 'status-good';
            case 'tired':
            case 'worried':
                return 'status-warning';
            case 'sad':
            case 'anxious':
                return 'status-danger';
            default:
                return 'status-warning';
        }
    }

    toggleVisitDetails(button) {
        const card = button.closest('.visit-card');
        const details = card.querySelector('.visit-details');
        const icon = button.querySelector('i');
        
        if (details.style.display === 'none') {
            details.style.display = 'block';
            icon.className = 'fas fa-chevron-up me-1';
            button.innerHTML = '<i class="fas fa-chevron-up me-1"></i> Hide Details';
        } else {
            details.style.display = 'none';
            icon.className = 'fas fa-chevron-down me-1';
            button.innerHTML = '<i class="fas fa-chevron-down me-1"></i> Show Details';
        }
    }

    async viewProfile(patientId) {
        this.showLoading();
        try {
            const response = await fetch(`/api/patients/${patientId}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderProfile(data.patient);
                const modal = new bootstrap.Modal(document.getElementById('profileModal'));
                modal.show();
            } else {
                console.error('Error loading patient profile:', data.error);
            }
        } catch (error) {
            console.error('Error loading patient profile:', error);
        } finally {
            this.hideLoading();
        }
    }

    renderProfile(patient) {
        const container = document.getElementById('profile-container');
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="profile-section">
                        <h6><i class="fas fa-user me-2"></i>Basic Information</h6>
                        <div class="detail-row">
                            <span class="detail-label">Name:</span>
                            <span class="detail-value">${patient.preferredName || patient.firstName} ${patient.lastName || ''}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Age:</span>
                            <span class="detail-value">${patient.age || 'N/A'} years old</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Gender:</span>
                            <span class="detail-value">${patient.gender || 'N/A'}</span>
                        </div>
                    </div>

                    <div class="profile-section">
                        <h6><i class="fas fa-stethoscope me-2"></i>Medical Conditions</h6>
                        ${this.renderConditions(patient.conditions || [])}
                    </div>

                    <div class="profile-section">
                        <h6><i class="fas fa-pills me-2"></i>Medications</h6>
                        ${this.renderMedications(patient.conditions || [])}
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="profile-section">
                        <h6><i class="fas fa-heart me-2"></i>Interests & Activities</h6>
                        ${this.renderInterests(patient.interests || [])}
                    </div>

                    <div class="profile-section">
                        <h6><i class="fas fa-clock me-2"></i>Daily Schedule</h6>
                        ${this.renderSchedule(patient.dailySchedule || [])}
                    </div>

                    <div class="profile-section">
                        <h6><i class="fas fa-users me-2"></i>Family & Caregiver</h6>
                        ${this.renderFamily(patient.family || [], patient.caregiver || {})}
                    </div>
                </div>
            </div>
        `;
    }

    renderConditions(conditions) {
        if (conditions.length === 0) {
            return '<p class="text-muted">No conditions recorded</p>';
        }
        
        return conditions.map(condition => `
            <div class="condition-badge">
                <strong>${condition.name}</strong>
                ${condition.severity ? ` (${condition.severity})` : ''}
                ${condition.notes ? `<br><small>${condition.notes}</small>` : ''}
            </div>
        `).join('');
    }

    renderMedications(conditions) {
        const medications = [];
        conditions.forEach(condition => {
            if (condition.medications) {
                medications.push(...condition.medications);
            }
        });
        
        if (medications.length === 0) {
            return '<p class="text-muted">No medications recorded</p>';
        }
        
        return medications.map(med => `
            <div class="medication-item">
                <strong>${med.name}</strong>
                ${med.dosage ? ` - ${med.dosage}` : ''}
                ${med.frequency ? ` (${med.frequency})` : ''}
                ${med.reminderTimes ? `<br><small>Reminders: ${med.reminderTimes.join(', ')}</small>` : ''}
            </div>
        `).join('');
    }

    renderInterests(interests) {
        if (interests.length === 0) {
            return '<p class="text-muted">No interests recorded</p>';
        }
        
        return interests.map(interest => `
            <span class="interest-tag">${interest}</span>
        `).join('');
    }

    renderSchedule(schedule) {
        if (schedule.length === 0) {
            return '<p class="text-muted">No schedule recorded</p>';
        }
        
        return schedule.map(item => `
            <div class="detail-row">
                <span class="detail-label">${item.event}:</span>
                <span class="detail-value">${item.time}</span>
            </div>
        `).join('');
    }

    renderFamily(family, caregiver) {
        let html = '';
        
        if (caregiver.name) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Primary Caregiver:</span>
                    <span class="detail-value">${caregiver.name} (${caregiver.relationship || 'caregiver'})</span>
                </div>
            `;
        }
        
        if (family.length > 0) {
            html += '<div class="mt-2"><strong>Family Members:</strong></div>';
            family.forEach(member => {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">${member.relation}:</span>
                        <span class="detail-value">${member.location || member.count || 'N/A'}</span>
                    </div>
                `;
            });
        }
        
        return html || '<p class="text-muted">No family information recorded</p>';
    }

    createAnalyticsCharts(visits) {
        // Destroy existing charts
        this.destroyCharts();
        
        // Sort visits by timestamp (oldest first)
        const sortedVisits = visits.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Create charts
        this.createMoodChart(sortedVisits);
        this.createPainChart(sortedVisits);
        this.createMedicationChart(sortedVisits);
        this.createFoodChart(sortedVisits);
        this.createSleepChart(sortedVisits);
        this.createHospitalizationChart(sortedVisits);
        this.createSummaryStats(sortedVisits);
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {};
    }

    createMoodChart(visits) {
        const ctx = document.getElementById('moodChart');
        if (!ctx) return;

        const labels = visits.map(visit => {
            const date = new Date(visit.timestamp);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const moodData = visits.map(visit => {
            const mood = visit.summary?.mood || 'neutral';
            return this.getMoodScore(mood);
        });

        this.charts.mood = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mood Score',
                    data: moodData,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 5,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                const moods = ['Very Low', 'Low', 'Neutral', 'Good', 'Excellent'];
                                return moods[value - 1] || value;
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createPainChart(visits) {
        const ctx = document.getElementById('painChart');
        if (!ctx) return;

        const labels = visits.map(visit => {
            const date = new Date(visit.timestamp);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const painData = visits.map(visit => visit.summary?.painReport || 0);

        this.charts.pain = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Pain Level',
                    data: painData,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        ticks: {
                            stepSize: 2
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createMedicationChart(visits) {
        const ctx = document.getElementById('medicationChart');
        if (!ctx) return;

        const taken = visits.filter(visit => visit.summary?.medicationsTaken).length;
        const missed = visits.filter(visit => !visit.summary?.medicationsTaken).length;

        this.charts.medication = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Taken', 'Missed'],
                datasets: [{
                    data: [taken, missed],
                    backgroundColor: ['#198754', '#dc3545'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createFoodChart(visits) {
        const ctx = document.getElementById('foodChart');
        if (!ctx) return;

        const foodCounts = {};
        visits.forEach(visit => {
            const foodIntake = visit.summary?.foodIntake || 'unknown';
            foodCounts[foodIntake] = (foodCounts[foodIntake] || 0) + 1;
        });

        const labels = Object.keys(foodCounts);
        const data = Object.values(foodCounts);

        this.charts.food = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Food Intake',
                    data: data,
                    backgroundColor: [
                        '#198754', // normal
                        '#ffc107', // low
                        '#dc3545', // none
                        '#6c757d'  // unknown
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createSleepChart(visits) {
        const ctx = document.getElementById('sleepChart');
        if (!ctx) return;

        const sleepCounts = {};
        visits.forEach(visit => {
            const sleepQuality = visit.summary?.sleepQuality || 'unknown';
            sleepCounts[sleepQuality] = (sleepCounts[sleepQuality] || 0) + 1;
        });

        const labels = Object.keys(sleepCounts);
        const data = Object.values(sleepCounts);

        this.charts.sleep = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sleep Quality',
                    data: data,
                    backgroundColor: [
                        '#198754', // good
                        '#0dcaf0', // normal
                        '#ffc107', // poor
                        '#6c757d'  // unknown
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createHospitalizationChart(visits) {
        const ctx = document.getElementById('hospitalizationChart');
        if (!ctx) return;

        const hospitalizationCounts = {};
        visits.forEach(visit => {
            const hospitalizationRisk = visit.openaiAnalysis?.hospitalizationPrediction?.riskLevel || 'LOW';
            hospitalizationCounts[hospitalizationRisk] = (hospitalizationCounts[hospitalizationRisk] || 0) + 1;
        });

        const labels = Object.keys(hospitalizationCounts);
        const data = Object.values(hospitalizationCounts);

        this.charts.hospitalization = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#dc3545', // HIGH
                        '#ffc107', // MEDIUM
                        '#198754'  // LOW
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createSummaryStats(visits) {
        const container = document.getElementById('summary-stats');
        if (!container) return;

        // Calculate statistics
        const totalVisits = visits.length;
        const avgPain = visits.reduce((sum, visit) => sum + (visit.summary?.painReport || 0), 0) / totalVisits;
        const medicationAdherence = (visits.filter(v => v.summary?.medicationsTaken).length / totalVisits * 100).toFixed(1);
        const avgMood = visits.reduce((sum, visit) => sum + this.getMoodScore(visit.summary?.mood || 'neutral'), 0) / totalVisits;
        
        // Most common food intake
        const foodCounts = {};
        visits.forEach(visit => {
            const food = visit.summary?.foodIntake || 'unknown';
            foodCounts[food] = (foodCounts[food] || 0) + 1;
        });
        const mostCommonFood = Object.keys(foodCounts).reduce((a, b) => foodCounts[a] > foodCounts[b] ? a : b);

        // Most common sleep quality
        const sleepCounts = {};
        visits.forEach(visit => {
            const sleep = visit.summary?.sleepQuality || 'unknown';
            sleepCounts[sleep] = (sleepCounts[sleep] || 0) + 1;
        });
        const mostCommonSleep = Object.keys(sleepCounts).reduce((a, b) => sleepCounts[a] > sleepCounts[b] ? a : b);

        // Hospitalization risk statistics
        const highRiskVisits = visits.filter(visit => 
            visit.openaiAnalysis?.hospitalizationPrediction?.riskLevel === 'HIGH'
        ).length;
        const highRiskPercentage = ((highRiskVisits / totalVisits) * 100).toFixed(1);

        container.innerHTML = `
            <div class="row">
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-primary mb-1">${totalVisits}</h4>
                        <small class="text-muted">Total Visits</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-success mb-1">${medicationAdherence}%</h4>
                        <small class="text-muted">Medication Adherence</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-warning mb-1">${avgPain.toFixed(1)}</h4>
                        <small class="text-muted">Avg Pain Level</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-info mb-1">${avgMood.toFixed(1)}</h4>
                        <small class="text-muted">Avg Mood Score</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-primary mb-1">${mostCommonFood}</h4>
                        <small class="text-muted">Most Common Food Intake</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-info mb-1">${mostCommonSleep}</h4>
                        <small class="text-muted">Most Common Sleep Quality</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-danger mb-1">${highRiskPercentage}%</h4>
                        <small class="text-muted">High Hospitalization Risk</small>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-center">
                        <h4 class="text-warning mb-1">${highRiskVisits}</h4>
                        <small class="text-muted">High Risk Visits</small>
                    </div>
                </div>
            </div>
        `;
    }

    getMoodScore(mood) {
        const moodScores = {
            'cheerful': 5,
            'happy': 5,
            'good': 4,
            'fine': 3,
            'neutral': 3,
            'tired': 2,
            'worried': 2,
            'sad': 1,
            'anxious': 1
        };
        return moodScores[mood] || 3;
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new Dashboard();
}); 