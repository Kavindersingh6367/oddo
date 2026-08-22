/**
 * GlobeTrotter — Frontend Single Page Application
 * Production-quality state management, dynamic budgeting, travel intelligence, and Odoo REST API client.
 */

// ================= App State =================
const state = {
    user: null,
    token: localStorage.getItem('gt_token') || null,
    currentPage: 'dashboard',
    trips: [],
    currentTripId: null,
    currentTrip: null,
    destinations: [],
    activities: [],
    viewMode: 'builder', // 'builder' | 'calendar' | 'timeline' | 'presentation' | 'budget'
    sharedToken: null,
    sharedTrip: null,
    searchQuery: '',
    selectedRegion: 'all',
    selectedCategory: 'all'
};

// ================= API Client =================
async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
        headers['X-Session-Token'] = state.token;
    }

    const options = {
        method,
        headers
    };
    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        if (!response.ok && !data.error) {
            throw new Error(`HTTP Error ${response.status}`);
        }
        return data;
    } catch (err) {
        console.error("API Request Error:", err);
        return { success: false, error: err.message || 'Network error' };
    }
}

// ================= Notification Toast Helper =================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-circle-exclamation';
    if (type === 'info') icon = 'fa-circle-info';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatCurrency(amount, currency = 'INR') {
    const num = Number(amount) || 0;
    const symMap = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'AED': 'AED ',
        'SGD': 'S$'
    };
    const sym = symMap[currency] || (currency + ' ');
    return `${sym}${num.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function formatDateRange(start, end) {
    if (!start || !end) return 'Dates pending';
    try {
        const s = new Date(start);
        const e = new Date(end);
        const sStr = s.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const eStr = e.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        return `${sStr} — ${eStr}`;
    } catch(err) {
        return `${start} — ${end}`;
    }
}

// ================= Authentication =================
async function initAuth() {
    if (state.token) {
        const res = await apiRequest('/api/v1/auth/me');
        if (res.success && res.user) {
            state.user = res.user;
        } else {
            state.token = null;
            localStorage.removeItem('gt_token');
        }
    }
    renderAuthNav();
}

function renderAuthNav() {
    const section = document.getElementById('auth-section');
    const adminNav = document.getElementById('nav-admin');
    
    if (adminNav) {
        adminNav.style.display = (state.user && state.user.role === 'admin') ? 'inline-flex' : 'none';
    }

    if (!section) return;

    if (state.user) {
        section.innerHTML = `
            <div class="auth-user-pill" onclick="openProfileModal()">
                <div class="user-avatar">${state.user.name.charAt(0).toUpperCase()}</div>
                <span class="user-name-tag">${escapeHtml(state.user.name.split(' ')[0])}</span>
                ${state.user.role === 'admin' ? '<span class="role-badge">Admin</span>' : ''}
            </div>
            <button class="btn btn-subtle btn-sm" onclick="handleLogout()" title="Log out">
                <i class="fa-solid fa-arrow-right-from-bracket"></i>
            </button>
        `;
    } else {
        section.innerHTML = `
            <button class="btn btn-outline btn-sm" onclick="openLoginModal()">Log In</button>
            <button class="btn btn-primary btn-sm" onclick="openSignupModal()">Sign Up</button>
        `;
    }
}

async function handleLogin(email, password) {
    const res = await apiRequest('/api/v1/auth/login', 'POST', { email, password });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Welcome back, ${state.user.name}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Login failed', 'error');
    }
}

async function handleDemoLogin(role = 'traveler') {
    const res = await apiRequest('/api/v1/auth/demo-login', 'POST', { role });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Signed in as demo ${role === 'admin' ? 'Administrator' : 'Traveler'}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Demo login failed', 'error');
    }
}

async function handleSignup(name, email, password, currency, travelStyle) {
    const res = await apiRequest('/api/v1/auth/signup', 'POST', {
        name, email, password, preferred_currency: currency, preferred_travel_style: travelStyle
    });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Welcome to GlobeTrotter, ${state.user.name}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Registration failed', 'error');
    }
}

async function handleLogout() {
    await apiRequest('/api/v1/auth/logout', 'POST');
    state.token = null;
    state.user = null;
    localStorage.removeItem('gt_token');
    renderAuthNav();
    showToast('Logged out successfully.');
    navigateTo('dashboard');
}

// ================= Navigation Routing =================
function navigateTo(page, param = null) {
    state.currentPage = page;
    
    // Update top nav active state
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    const main = document.getElementById('main-content');
    if (!main) return;

    if (page === 'dashboard') {
        renderDashboard();
    } else if (page === 'trips') {
        renderTripsList();
    } else if (page === 'itinerary') {
        if (param) state.currentTripId = param;
        renderItineraryBuilder();
    } else if (page === 'destinations') {
        renderDestinationsCatalog();
    } else if (page === 'activities') {
        renderActivitiesCatalog();
    } else if (page === 'community') {
        renderCommunityHub();
    } else if (page === 'admin') {
        renderAdminDashboard();
    } else if (page === 'shared') {
        if (param) state.sharedToken = param;
        renderPublicSharedTrip();
    }
}

// ================= View 1: Dashboard =================
async function renderDashboard() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading GlobeTrotter dashboard...</div>`;

    // Fetch user trips & destinations
    let trips = [];
    if (state.user) {
        const tRes = await apiRequest('/api/v1/trips');
        if (tRes.success) {
            trips = tRes.trips || [];
            state.trips = trips;
        }
    }

    const dRes = await apiRequest('/api/v1/destinations');
    const destinations = dRes.success ? (dRes.destinations || []) : [];
    state.destinations = destinations;

    // Calculate Dashboard KPIs
    const totalTrips = trips.length;
    const activeTrips = trips.filter(t => t.status === 'upcoming' || t.status === 'ongoing').length;
    const totalBudget = trips.reduce((sum, t) => sum + Number(t.total_budget || 0), 0);
    const upcomingTrip = trips.find(t => t.status === 'upcoming' || t.status === 'ongoing') || trips[0];

    const upcomingDest = (upcomingTrip && upcomingTrip.stops_count > 0) ? `${upcomingTrip.name}` : (trips.length > 0 ? trips[0].name : 'Rajasthan Explorer');

    let html = `
        <!-- Hero Section -->
        <div class="dashboard-hero">
            <div class="hero-content">
                <div class="hero-badge">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> Personalized Itinerary Engine
                </div>
                <h1 class="hero-title">${state.user ? `Welcome back, ${escapeHtml(state.user.name.split(' ')[0])}!` : 'Design Your Perfect Journey with GlobeTrotter'}</h1>
                <p class="hero-desc">
                    Seamlessly assemble multi-city itineraries, discover curated activities, optimize trip budgets in real time, and share your adventures with a single click.
                </p>
                <div class="hero-actions">
                    <button class="btn btn-accent btn-lg btn-glow" onclick="openCreateTripModal()">
                        <i class="fa-solid fa-plus"></i> Plan New Trip
                    </button>
                    ${!state.user ? `
                        <button class="btn btn-outline btn-lg" onclick="handleDemoLogin('traveler')">
                            <i class="fa-solid fa-bolt"></i> 1-Click Demo Traveler
                        </button>
                        <button class="btn btn-subtle btn-lg" onclick="handleDemoLogin('admin')">
                            <i class="fa-solid fa-shield-halved"></i> 1-Click Admin Demo
                        </button>
                    ` : `
                        <button class="btn btn-outline btn-lg" onclick="navigateTo('destinations')">
                            <i class="fa-solid fa-compass"></i> Discover Destinations
                        </button>
                    `}
                </div>
            </div>
        </div>

        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon-wrap indigo"><i class="fa-solid fa-suitcase-rolling"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Itineraries</span>
                    <span class="kpi-val">${totalTrips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap emerald"><i class="fa-solid fa-paper-plane"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Active / Upcoming</span>
                    <span class="kpi-val">${activeTrips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap amber"><i class="fa-solid fa-wallet"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Trip Budgets</span>
                    <span class="kpi-val">${formatCurrency(totalBudget, state.user ? state.user.preferred_currency : 'INR')}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap sky"><i class="fa-solid fa-map-pin"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Next Destination</span>
                    <span class="kpi-val" style="font-size: 1.25rem;">${escapeHtml(upcomingDest)}</span>
                </div>
            </div>
        </div>

        ${(state.user && state.user.travel_dna) ? `
            <!-- Travel DNA Engine Profile Card -->
            <div class="travel-dna-card">
                <div class="travel-dna-header">
                    <div>
                        <div class="travel-dna-title">
                            <i class="fa-solid fa-dna" style="color: #F97316;"></i> Travel DNA Profile
                        </div>
                        <div style="font-size: 0.85rem; color: #C7D2FE; margin-top: 0.2rem;">
                            AI-modeled travel persona based on your destinations, activity choices, and pacing preferences.
                        </div>
                    </div>
                    <span class="persona-badge-glow">
                        <i class="fa-solid fa-sparkles"></i> ${escapeHtml(state.user.travel_dna.persona_title || 'Balanced Explorer')}
                    </span>
                </div>
                <div class="dna-bars-grid">
                    <div class="dna-bar-item">
                        <div class="dna-bar-header">
                            <span><i class="fa-solid fa-mountain" style="color: #F97316;"></i> Adventure</span>
                            <span>${state.user.travel_dna.adventure || 50}%</span>
                        </div>
                        <div class="dna-bar-track"><div class="dna-bar-fill adventure" style="width: ${state.user.travel_dna.adventure || 50}%;"></div></div>
                    </div>
                    <div class="dna-bar-item">
                        <div class="dna-bar-header">
                            <span><i class="fa-solid fa-landmark-dome" style="color: #818CF8;"></i> Culture &amp; History</span>
                            <span>${state.user.travel_dna.culture || 65}%</span>
                        </div>
                        <div class="dna-bar-track"><div class="dna-bar-fill culture" style="width: ${state.user.travel_dna.culture || 65}%;"></div></div>
                    </div>
                    <div class="dna-bar-item">
                        <div class="dna-bar-header">
                            <span><i class="fa-solid fa-utensils" style="color: #F43F5E;"></i> Food &amp; Dining</span>
                            <span>${state.user.travel_dna.food || 70}%</span>
                        </div>
                        <div class="dna-bar-track"><div class="dna-bar-fill food" style="width: ${state.user.travel_dna.food || 70}%;"></div></div>
                    </div>
                    <div class="dna-bar-item">
                        <div class="dna-bar-header">
                            <span><i class="fa-solid fa-umbrella-beach" style="color: #34D399;"></i> Relaxation</span>
                            <span>${state.user.travel_dna.relaxation || 45}%</span>
                        </div>
                        <div class="dna-bar-track"><div class="dna-bar-fill relaxation" style="width: ${state.user.travel_dna.relaxation || 45}%;"></div></div>
                    </div>
                    <div class="dna-bar-item">
                        <div class="dna-bar-header">
                            <span><i class="fa-solid fa-camera" style="color: #38BDF8;"></i> Sightseeing</span>
                            <span>${state.user.travel_dna.sightseeing || 80}%</span>
                        </div>
                        <div class="dna-bar-track"><div class="dna-bar-fill sightseeing" style="width: ${state.user.travel_dna.sightseeing || 80}%;"></div></div>
                    </div>
                </div>
                <div class="dna-insights-list">
                    ${(state.user.travel_dna.insights || []).map(ins => `<div><i class="fa-solid fa-check" style="color: #34D399; margin-right: 0.4rem;"></i> ${escapeHtml(ins)}</div>`).join('')}
                </div>
            </div>
        ` : ''}

        <!-- Recent Trips Section -->
        <div class="section-header">
            <h2 class="section-title"><i class="fa-solid fa-calendar-days" style="color: var(--primary);"></i> Your Travel Plans</h2>
            <div style="display: flex; gap: 0.5rem;">
                <button class="btn btn-outline btn-sm" onclick="navigateTo('community')"><i class="fa-solid fa-users"></i> Community Hub</button>
                <button class="btn btn-outline btn-sm" onclick="navigateTo('trips')">View All Trips (${trips.length})</button>
                <button class="btn btn-primary btn-sm" onclick="openCreateTripModal()"><i class="fa-solid fa-plus"></i> New Trip</button>
            </div>
        </div>
    `;

    if (trips.length === 0) {
        html += `
            <div class="empty-state-box" style="background: #fff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); padding: 3rem; text-align: center; margin-bottom: 2.5rem;">
                <div style="font-size: 3rem; color: var(--primary); margin-bottom: 1rem;"><i class="fa-solid fa-map-location-dot"></i></div>
                <h3 style="margin-bottom: 0.5rem;">You haven't planned a trip yet.</h3>
                <p style="color: var(--text-muted); max-width: 480px; margin: 0 auto 1.5rem;">
                    Start your travel story! Choose your cities, assign dates, add activities, and watch your budget balance itself automatically.
                </p>
                <button class="btn btn-primary btn-lg" onclick="openCreateTripModal()">
                    <i class="fa-solid fa-plus"></i> Plan Your First Trip
                </button>
            </div>
        `;
    } else {
        html += `<div class="trip-grid">`;
        trips.slice(0, 6).forEach(trip => {
            const util = trip.budget_utilization || 0;
            let barClass = 'normal';
            if (util > 100) barClass = 'danger';
            else if (util >= 85) barClass = 'warning';

            html += `
                <div class="trip-card" onclick="navigateTo('itinerary', ${trip.id})">
                    <div class="trip-card-cover">
                        <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(trip.name)}" loading="lazy">
                        <span class="trip-status-tag ${trip.status}">${trip.status}</span>
                        <span class="trip-style-tag">${escapeHtml(trip.travel_style || 'Balanced')}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(trip.name)}</h3>
                        <div class="trip-dates">
                            <i class="fa-regular fa-calendar"></i>
                            ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)
                        </div>
                        <div class="trip-meta-row">
                            <div class="trip-meta-item"><i class="fa-solid fa-city"></i> ${trip.stops_count || 0} Cities</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${trip.activities_count || 0} Acts</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-users"></i> ${trip.travelers_count || 1}</div>
                        </div>
                        <div class="trip-budget-progress">
                            <div class="progress-header">
                                <span>Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                                <span>${util.toFixed(0)}%</span>
                            </div>
                            <div class="progress-bar-track">
                                <div class="progress-bar-fill ${barClass}" style="width: ${Math.min(100, util)}%;"></div>
                            </div>
                        </div>
                        <div class="trip-card-actions">
                            <span class="badge-chip score" title="Trip Balance Score">
                                <i class="fa-solid fa-gauge-high"></i> Score: ${trip.trip_balance_score || 75}/100
                            </span>
                            <span style="font-weight: 700; color: var(--primary); font-size: 0.88rem;">Open Plan &rarr;</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    // Recommended Destinations Carousel
    html += `
        <div class="section-header" style="margin-top: 2rem;">
            <h2 class="section-title"><i class="fa-solid fa-fire" style="color: var(--accent);"></i> Trending Travel Destinations</h2>
            <button class="btn btn-outline btn-sm" onclick="navigateTo('destinations')">Explore All Destinations</button>
        </div>
        <div class="trip-grid">
    `;

    destinations.slice(0, 4).forEach(dest => {
        html += `
            <div class="trip-card" onclick="openDestinationDetailModal(${dest.id})">
                <div class="trip-card-cover">
                    <img src="${dest.cover_image}" alt="${escapeHtml(dest.name)}" loading="lazy">
                    <span class="trip-status-tag" style="background: rgba(15, 23, 42, 0.85); color: #FDBA74;">
                        <i class="fa-solid fa-star"></i> ${dest.popularity}/100
                    </span>
                    <span class="trip-style-tag">${escapeHtml(dest.country)}</span>
                </div>
                <div class="trip-card-body">
                    <h3 class="trip-card-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h3>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                        ${escapeHtml(dest.description.substring(0, 90))}...
                    </p>
                    <div class="trip-meta-row" style="margin-top: auto;">
                        <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Rec: ${dest.recommended_duration_days} Days</div>
                        <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost: ${'₹'.repeat(dest.cost_index || 2)}</div>
                    </div>
                    <div class="trip-card-actions">
                        <button class="btn btn-subtle btn-sm" onclick="event.stopPropagation(); openAddToTripModal(${dest.id})">
                            <i class="fa-solid fa-plus"></i> Add to Trip
                        </button>
                        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openDestinationDetailModal(${dest.id})">
                            View Activities
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    main.innerHTML = html;
}

// ================= View 2: My Trips List =================
async function renderTripsList(statusFilter = 'all') {
    const main = document.getElementById('main-content');
    if (!state.user) {
        main.innerHTML = `
            <div style="background: #fff; border-radius: var(--radius-lg); padding: 3rem; text-align: center; border: 1px solid var(--border-color);">
                <h2>Please log in to manage your itineraries</h2>
                <p style="color: var(--text-muted); margin: 0.75rem 0 1.5rem;">Track, budget, and share your multi-city journeys in one place.</p>
                <button class="btn btn-primary" onclick="openLoginModal()">Log In</button>
            </div>
        `;
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading your itineraries...</div>`;
    const res = await apiRequest(`/api/v1/trips?status=${statusFilter}`);
    const trips = res.success ? (res.trips || []) : [];
    state.trips = trips;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">My Itineraries</h1>
                <p style="color: var(--text-muted);">Manage, duplicate, and schedule your custom travel journeys.</p>
            </div>
            <button class="btn btn-primary" onclick="openCreateTripModal()">
                <i class="fa-solid fa-plus"></i> Plan New Trip
            </button>
        </div>

        <!-- Filter Tabs -->
        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
            <button class="btn btn-sm ${statusFilter === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('all')">All Trips</button>
            <button class="btn btn-sm ${statusFilter === 'upcoming' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('upcoming')">Upcoming</button>
            <button class="btn btn-sm ${statusFilter === 'ongoing' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('ongoing')">Ongoing</button>
            <button class="btn btn-sm ${statusFilter === 'completed' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('completed')">Completed</button>
            <button class="btn btn-sm ${statusFilter === 'draft' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('draft')">Drafts</button>
        </div>
    `;

    if (trips.length === 0) {
        html += `
            <div style="background: #fff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); padding: 3.5rem; text-align: center;">
                <i class="fa-solid fa-plane-slash" style="font-size: 3rem; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No itineraries found in this section</h3>
                <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Create a trip to organize destinations, activities, and dynamic budgets.</p>
                <button class="btn btn-primary" onclick="openCreateTripModal()"><i class="fa-solid fa-plus"></i> Plan a Trip</button>
            </div>
        `;
    } else {
        html += `<div class="trip-grid">`;
        trips.forEach(trip => {
            const util = trip.budget_utilization || 0;
            let barClass = 'normal';
            if (util > 100) barClass = 'danger';
            else if (util >= 85) barClass = 'warning';

            html += `
                <div class="trip-card" onclick="navigateTo('itinerary', ${trip.id})">
                    <div class="trip-card-cover">
                        <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(trip.name)}" loading="lazy">
                        <span class="trip-status-tag ${trip.status}">${trip.status}</span>
                        <span class="trip-style-tag">${escapeHtml(trip.travel_style || 'Balanced')}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(trip.name)}</h3>
                        <div class="trip-dates">
                            <i class="fa-regular fa-calendar"></i>
                            ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)
                        </div>
                        <div class="trip-meta-row">
                            <div class="trip-meta-item"><i class="fa-solid fa-city"></i> ${trip.stops_count || 0} Stops</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${trip.activities_count || 0} Acts</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-users"></i> ${trip.travelers_count || 1}</div>
                        </div>
                        <div class="trip-budget-progress">
                            <div class="progress-header">
                                <span>Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                                <span>${util.toFixed(0)}%</span>
                            </div>
                            <div class="progress-bar-track">
                                <div class="progress-bar-fill ${barClass}" style="width: ${Math.min(100, util)}%;"></div>
                            </div>
                        </div>
                        <div class="trip-card-actions" onclick="event.stopPropagation();">
                            <div style="display: flex; gap: 0.35rem;">
                                <button class="btn btn-subtle btn-sm" onclick="handleDuplicateTrip(${trip.id})" title="Duplicate Itinerary"><i class="fa-regular fa-copy"></i></button>
                                <button class="btn btn-subtle btn-sm" onclick="openShareModal(${trip.id})" title="Share Itinerary"><i class="fa-solid fa-share-nodes"></i></button>
                                <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteTrip(${trip.id})" title="Delete Itinerary"><i class="fa-regular fa-trash-can"></i></button>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="navigateTo('itinerary', ${trip.id})">Open Builder</button>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }
    main.innerHTML = html;
}

// ================= View 3: Central Itinerary Builder =================
async function renderItineraryBuilder() {
    const main = document.getElementById('main-content');
    if (!state.currentTripId) {
        navigateTo('trips');
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading full itinerary plan & intelligence...</div>`;

    const res = await apiRequest(`/api/v1/trips/${state.currentTripId}`);
    if (!res.success || !res.trip) {
        showToast(res.error || 'Failed to load trip', 'error');
        navigateTo('trips');
        return;
    }

    const trip = res.trip;
    state.currentTrip = trip;

    let html = `
        <!-- Itinerary Header Banner -->
        <div class="itinerary-header-banner">
            <div class="itinerary-top-row">
                <div class="itinerary-title-block">
                    <h1>${escapeHtml(trip.name)}</h1>
                    <div class="itinerary-chips-row">
                        <span class="badge-chip primary"><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span class="badge-chip accent"><i class="fa-solid fa-users"></i> ${trip.travelers_count} Traveler${trip.travelers_count > 1 ? 's' : ''}</span>
                        <span class="badge-chip success"><i class="fa-solid fa-wallet"></i> Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                        <span class="badge-chip"><i class="fa-solid fa-compass"></i> Style: ${escapeHtml(trip.travel_style || 'Balanced')}</span>
                        <span class="badge-chip score"><i class="fa-solid fa-gauge-high"></i> Balance Score: ${trip.trip_balance_score}/100</span>
                        ${(trip.hotels && trip.hotels.length > 0) ? `
                            <span class="badge-chip" style="background: #F5F3FF; color: #6B21A8; border-color: #DDD6FE;">
                                <i class="fa-solid fa-hotel"></i> ${trip.hotels.length} Hotel${trip.hotels.length > 1 ? 's' : ''} (${formatCurrency(trip.hotels.reduce((s, h) => s + Number(h.total_cost || 0), 0), trip.currency)})
                            </span>
                        ` : ''}
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-outline btn-sm" onclick="openEditTripModal(${trip.id})"><i class="fa-solid fa-pen"></i> Edit Details</button>
                    <button class="btn btn-accent btn-sm" onclick="openShareModal(${trip.id})"><i class="fa-solid fa-share-nodes"></i> Share Publicly</button>
                    <button class="btn btn-subtle btn-sm" onclick="handleDuplicateTrip(${trip.id})"><i class="fa-regular fa-copy"></i> Duplicate</button>
                </div>
            </div>

            <!-- View Switcher Toolbar -->
            <div class="itinerary-actions-bar">
                <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                    <button class="btn btn-sm ${state.viewMode === 'builder' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('builder')">
                        <i class="fa-solid fa-list-check"></i> Itinerary Builder
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'calendar' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('calendar')">
                        <i class="fa-regular fa-calendar-days"></i> Calendar View
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'timeline' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('timeline')">
                        <i class="fa-solid fa-route"></i> Timeline View
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'budget' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('budget')">
                        <i class="fa-solid fa-chart-pie"></i> Budget &amp; Intelligence
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'presentation' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('presentation')">
                        <i class="fa-solid fa-tv"></i> Presentation Mode
                    </button>
                </div>
                <div style="margin-left: auto; display: flex; gap: 0.5rem;">
                    <button class="btn btn-primary btn-sm" onclick="openAddStopModal(${trip.id})"><i class="fa-solid fa-location-dot"></i> + Add City Stop</button>
                    <button class="btn btn-outline btn-sm" onclick="openAddExpenseModal(${trip.id})"><i class="fa-solid fa-receipt"></i> + Add Expense</button>
                </div>
            </div>
        </div>
    `;

    // Render Sub-Views based on state.viewMode
    if (state.viewMode === 'builder') {
        html += renderBuilderScheduleView(trip);
    } else if (state.viewMode === 'calendar') {
        html += renderCalendarGridView(trip);
    } else if (state.viewMode === 'timeline') {
        html += renderVerticalTimelineView(trip);
    } else if (state.viewMode === 'budget') {
        html += renderBudgetAndIntelligenceView(trip);
    } else if (state.viewMode === 'presentation') {
        html += renderPresentationView(trip);
    }

    main.innerHTML = html;
}

function switchItineraryView(mode) {
    state.viewMode = mode;
    renderItineraryBuilder();
}

// ================= Builder Sub-View: Stops Rail + Day Schedule =================
function renderBuilderScheduleView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;
    const health = trip.trip_health || null;
    const balancing = trip.balancing_suggestions || [];

    let html = ``;

    // 1. Trip Health & Diagnostics Widget
    if (health) {
        let badgeColor = 'emerald';
        if (health.health_score < 60) badgeColor = 'rose';
        else if (health.health_score < 80) badgeColor = 'amber';

        const bk = health.breakdown || {};
        html += `
            <div class="trip-health-card">
                <div class="health-header-row">
                    <div class="health-score-container">
                        <div class="health-circle-badge ${badgeColor}">
                            <span class="health-circle-num">${health.health_score}</span>
                            <span class="health-circle-label">HEALTH</span>
                        </div>
                        <div>
                            <h3 style="font-size: 1.2rem; margin-bottom: 0.2rem;">
                                Trip Health Diagnostics: <span style="color: var(--primary);">${escapeHtml(health.verdict || 'Good Balance')}</span>
                            </h3>
                            <div style="font-size: 0.85rem; color: var(--text-muted);">
                                Multi-factor intelligence score evaluating budget discipline, pacing, daily density, and accommodation coverage.
                            </div>
                        </div>
                    </div>
                </div>

                <div class="health-dimensions-grid">
                    <div class="health-dim-item">
                        <div class="health-dim-top">
                            <span>Budget Discipline</span>
                            <span>${bk.budget_health || 25}/30</span>
                        </div>
                        <div class="health-dim-track"><div class="health-dim-fill" style="width: ${((bk.budget_health || 25)/30)*100}%;"></div></div>
                    </div>
                    <div class="health-dim-item">
                        <div class="health-dim-top">
                            <span>Activity Density</span>
                            <span>${bk.activity_load || 20}/25</span>
                        </div>
                        <div class="health-dim-track"><div class="health-dim-fill" style="width: ${((bk.activity_load || 20)/25)*100}%;"></div></div>
                    </div>
                    <div class="health-dim-item">
                        <div class="health-dim-top">
                            <span>City Dwell Pacing</span>
                            <span>${bk.city_pacing || 18}/20</span>
                        </div>
                        <div class="health-dim-track"><div class="health-dim-fill" style="width: ${((bk.city_pacing || 18)/20)*100}%;"></div></div>
                    </div>
                    <div class="health-dim-item">
                        <div class="health-dim-top">
                            <span>Hotel Coverage</span>
                            <span>${bk.hotel_coverage || 10}/15</span>
                        </div>
                        <div class="health-dim-track"><div class="health-dim-fill" style="width: ${((bk.hotel_coverage || 10)/15)*100}%;"></div></div>
                    </div>
                    <div class="health-dim-item">
                        <div class="health-dim-top">
                            <span>Completeness</span>
                            <span>${bk.completeness || 8}/10</span>
                        </div>
                        <div class="health-dim-track"><div class="health-dim-fill" style="width: ${((bk.completeness || 8)/10)*100}%;"></div></div>
                    </div>
                </div>

                ${(health.actionable_recommendations && health.actionable_recommendations.length > 0) ? `
                    <div class="health-recs-box">
                        ${health.actionable_recommendations.map(rec => `
                            <div class="health-rec-item">
                                <div class="health-rec-text">
                                    <i class="fa-solid fa-lightbulb" style="margin-right: 0.4rem;"></i>
                                    ${escapeHtml(rec.message)}
                                </div>
                                ${rec.action === 'find_hotels' ? `
                                    <button class="btn btn-outline btn-sm" onclick="switchItineraryView('builder')">Browse Hotels</button>
                                ` : (rec.action === 'balance_activities' ? `
                                    <button class="btn btn-accent btn-sm" onclick="handleAcceptBalancing(${trip.id})">⚡ Balance</button>
                                ` : '')}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    // 2. Smart Itinerary Balancing Assistant Card
    if (balancing && balancing.length > 0) {
        html += `
            <div class="balancing-assistant-card">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div class="balancing-icon"><i class="fa-solid fa-scale-balanced"></i></div>
                    <div class="balancing-content">
                        <h4>Smart Itinerary Balancing Assistant</h4>
                        <p>${escapeHtml(balancing[0].reason)}</p>
                    </div>
                </div>
                <button class="btn btn-primary btn-glow" onclick="handleAcceptBalancing(${trip.id})">
                    <i class="fa-solid fa-bolt"></i> <span>Accept Suggestion</span>
                </button>
            </div>
        `;
    }

    html += `
        <!-- Multi-City Stops Rail -->
        <div class="stops-rail-container">
            <div class="stops-rail-header">
                <div>
                    <h3 style="font-size: 1.15rem;"><i class="fa-solid fa-map-location-dot" style="color: var(--primary);"></i> Multi-City Route Sequence</h3>
                    <p style="font-size: 0.82rem; color: var(--text-muted);">Reorder stops to optimize travel route and manage city accommodations.</p>
                </div>
                <button class="btn btn-outline btn-sm" onclick="openAddStopModal(${trip.id})">
                    <i class="fa-solid fa-plus"></i> Add Destination
                </button>
            </div>
            <div class="stops-scroll-track">
    `;

    if (stops.length === 0) {
        html += `
            <div style="padding: 1.5rem; text-align: center; width: 100%; color: var(--text-muted);">
                <i class="fa-solid fa-location-dot" style="font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--accent);"></i>
                <div>No destination stops added yet. Click <strong>+ Add Destination</strong> to start building your route.</div>
            </div>
        `;
    } else {
        stops.forEach((stop, index) => {
            const hasHotel = Boolean(stop.hotel_booking);
            html += `
                <div class="stop-sequence-card">
                    <span class="stop-seq-badge">${index + 1}</span>
                    <div class="stop-city-name">${escapeHtml(stop.city_name)}, ${escapeHtml(stop.country_name)}</div>
                    <div class="stop-dates-text">
                        <i class="fa-regular fa-calendar"></i> ${formatDateRange(stop.arrival_date, stop.departure_date)} (${stop.duration_days}d)
                    </div>
                    <div style="font-size: 0.78rem; margin: 0.35rem 0; padding: 0.2rem 0.4rem; background: ${hasHotel ? '#F0FDF4' : '#FAF5FF'}; border-radius: var(--radius-sm); color: ${hasHotel ? '#166534' : '#6B21A8'}; font-weight: 600;">
                        ${hasHotel ? `<i class="fa-solid fa-hotel"></i> ${escapeHtml(stop.hotel_booking.hotel_name.substring(0, 18))}...` : `<i class="fa-solid fa-bed"></i> No Hotel Booked`}
                    </div>
                    <div class="stop-card-controls">
                        <div style="display: flex; gap: 0.25rem;">
                            <button class="btn btn-subtle btn-sm" ${index === 0 ? 'disabled' : ''} onclick="handleMoveStop(${trip.id}, ${index}, -1)" title="Move Left"><i class="fa-solid fa-arrow-left"></i></button>
                            <button class="btn btn-subtle btn-sm" ${index === stops.length - 1 ? 'disabled' : ''} onclick="handleMoveStop(${trip.id}, ${index}, 1)" title="Move Right"><i class="fa-solid fa-arrow-right"></i></button>
                        </div>
                        <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteStop(${trip.id}, ${stop.id})" title="Remove City"><i class="fa-regular fa-trash-can"></i></button>
                    </div>
                </div>
            `;
            if (index < stops.length - 1) {
                html += `<div class="stop-arrow-connector"><i class="fa-solid fa-arrow-right-long"></i></div>`;
            }
        });
    }

    html += `
            </div>
        </div>

        <!-- City Accommodations & Hotels Section -->
        ${stops.length > 0 ? `
            <div style="margin-bottom: 2rem;">
                <div class="section-header" style="margin-bottom: 1rem;">
                    <div>
                        <h3 style="font-size: 1.2rem; display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fa-solid fa-hotel" style="color: var(--primary);"></i> Destination Accommodations &amp; Stays
                        </h3>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">Smart recommendations tailored to your itinerary dates, group size, and remaining budget.</p>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    ${stops.map(stop => {
                        if (stop.hotel_booking) {
                            const hb = stop.hotel_booking;
                            return `
                                <div class="stop-accommodation-card">
                                    <div class="stop-hotel-left">
                                        <img src="${hb.hotel_image || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=400&q=80'}" class="stop-hotel-thumb" alt="${escapeHtml(hb.hotel_name)}">
                                        <div class="stop-hotel-info">
                                            <h4>
                                                 <i class="fa-solid fa-hotel" style="color: var(--primary);"></i>
                                                ${escapeHtml(hb.hotel_name)}
                                                <span class="hotel-category-badge" style="position:static; margin-left: 0.4rem; padding: 0.15rem 0.5rem;">${escapeHtml((hb.hotel_category || 'hotel').replace('_', '-'))}</span>
                                            </h4>
                                            <div class="stop-hotel-meta">
                                                <span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(stop.city_name)}</span>
                                                <span><i class="fa-solid fa-star" style="color: #F59E0B;"></i> ${hb.hotel_rating || 4.5}/5.0</span>
                                                <span><i class="fa-regular fa-calendar"></i> ${hb.number_of_nights} Nights (${formatDateRange(hb.check_in, hb.check_out)})</span>
                                                <span><i class="fa-solid fa-door-open"></i> ${hb.number_of_rooms || 1} Room · ${hb.number_of_guests || 2} Guests</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="stop-hotel-right">
                                        <div>
                                            <div class="stop-hotel-cost">${formatCurrency(hb.total_cost, trip.currency)}</div>
                                            <div class="stop-hotel-nights">${formatCurrency(hb.price_per_night, trip.currency)} / night</div>
                                        </div>
                                        <div style="display: flex; gap: 0.35rem;">
                                            <button class="btn btn-subtle btn-sm" onclick="openEditHotelModal(${hb.id})" title="Edit Dates/Rooms"><i class="fa-solid fa-pen"></i></button>
                                            <button class="btn btn-outline btn-sm" onclick="openHotelSearchModal(${stop.id}, ${stop.city_id}, '${escapeHtml(stop.city_name)}', '${stop.arrival_date}', '${stop.departure_date}')" title="Change Hotel">Change</button>
                                            <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteHotelBooking(${hb.id})" title="Remove Hotel"><i class="fa-regular fa-trash-can"></i></button>
                                        </div>
                                    </div>
                                </div>
                            `;
                        } else {
                            return `
                                <div class="no-hotel-cta" onclick="openHotelSearchModal(${stop.id}, ${stop.city_id}, '${escapeHtml(stop.city_name)}', '${stop.arrival_date}', '${stop.departure_date}')">
                                    <div class="no-hotel-cta-text">
                                        <i class="fa-solid fa-bed"></i>
                                        <span>No hotel selected for <strong>${escapeHtml(stop.city_name)}</strong> (${formatDateRange(stop.arrival_date, stop.departure_date)}, ${stop.duration_days} nights)</span>
                                    </div>
                                    <button class="btn btn-primary btn-sm">
                                        <i class="fa-solid fa-magnifying-glass"></i> Find Recommended Hotels
                                    </button>
                                </div>
                            `;
                        }
                    }).join('')}
                </div>
            </div>
        ` : ''}

        <!-- Day-Wise Schedule Blocks -->
        <div class="section-header">
            <h2 class="section-title"><i class="fa-solid fa-calendar-check" style="color: var(--primary);"></i> Day-Wise Schedule &amp; Activity Sections</h2>
        </div>
    `;

    // Generate day blocks
    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        const dayActivities = activities.filter(a => Number(a.day_number) === dayNum);
        const dayCost = dayActivities.reduce((sum, a) => sum + Number(a.estimated_cost || 0), 0);

        html += `
            <div class="day-schedule-block">
                <div class="day-header">
                    <div class="day-header-left">
                        <span class="day-pill">DAY ${dayNum}</span>
                        <div class="day-title-text">${dayDateStr}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="font-weight: 700; font-size: 0.95rem; color: var(--text-muted);">
                            Daily Est: ${formatCurrency(dayCost, trip.currency)}
                        </span>
                        <button class="btn btn-primary btn-sm" onclick="openAddActivityModal(${trip.id}, ${dayNum})">
                            <i class="fa-solid fa-plus"></i> Add Section
                        </button>
                    </div>
                </div>
                <div class="day-activities-list">
        `;

        if (dayActivities.length === 0) {
            html += `
                <div style="padding: 1.25rem; text-align: center; color: var(--text-muted); background: var(--bg-main); border-radius: var(--radius-md);">
                    <span>No activities scheduled for Day ${dayNum}. Click <strong>+ Add Section</strong> to add sightseeing, transport, dining, or custom items.</span>
                </div>
            `;
        } else {
            dayActivities.forEach(act => {
                const secType = act.section_type || 'activity';
                html += `
                    <div class="activity-item-card">
                        <div class="act-left-block">
                            <div class="act-time-badge">${escapeHtml(act.scheduled_time || '10:00')}</div>
                            <div class="act-details">
                                <div style="display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap;">
                                    <span class="act-name">${escapeHtml(act.name)}</span>
                                    <span class="section-type-badge ${secType}">${secType}</span>
                                </div>
                                <div class="act-meta-tags">
                                    <span class="category-tag ${act.category || 'sightseeing'}">${escapeHtml(act.category || 'sightseeing')}</span>
                                    <span><i class="fa-regular fa-clock"></i> ${act.duration_hours || 2}h</span>
                                    ${act.city_name ? `<span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(act.city_name)}</span>` : ''}
                                    ${act.location_address ? `<span><i class="fa-solid fa-map-pin"></i> ${escapeHtml(act.location_address)}</span>` : ''}
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1.25rem;">
                            <div class="act-cost-badge">${formatCurrency(act.estimated_cost, trip.currency)}</div>
                            <div style="display: flex; gap: 0.35rem;">
                                <button class="btn btn-subtle btn-sm" onclick="openMoveActivityModal(${trip.id}, ${act.id}, ${dayNum}, ${durationDays})" title="Move to another Day"><i class="fa-solid fa-arrow-right-arrow-left"></i></button>
                                <button class="btn btn-subtle btn-sm" onclick="handleDuplicateActivity(${trip.id}, ${act.id})" title="Duplicate"><i class="fa-regular fa-clone"></i></button>
                                <button class="btn btn-subtle btn-sm" onclick="openEditActivityModal(${trip.id}, ${act.id})" title="Edit"><i class="fa-solid fa-pen"></i></button>
                                <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteActivity(${trip.id}, ${act.id})" title="Delete"><i class="fa-regular fa-trash-can"></i></button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        html += `
                </div>
            </div>
        `;
    }

    return html;
}

// ================= Builder Sub-View: Budget & Intelligence Engine =================
function renderBudgetAndIntelligenceView(trip) {
    const bd = trip.category_breakdown || {};
    const alerts = trip.budget_intelligence_alerts || [];
    const factors = trip.balance_score_summary || [];
    const expenses = trip.expenses || [];
    const util = trip.budget_utilization || 0;

    let html = `
        <!-- Travel Balance Score Gauge -->
        <div class="balance-score-container">
            <div class="score-gauge-box" style="--score-pct: ${trip.trip_balance_score || 80};">
                <span class="score-number">${trip.trip_balance_score || 80}</span>
                <span class="score-max">OUT OF 100</span>
            </div>
            <div style="flex: 1;">
                <h2 style="color: #fff; margin-bottom: 0.35rem; font-size: 1.6rem;">Trip Balance &amp; Pacing Score</h2>
                <p style="color: #C7D2FE; font-size: 0.9rem; margin-bottom: 1.25rem;">
                    Our transparent rating engine evaluates budget alignment, activity density, city dwell time, and logistic completeness.
                </p>
                <div class="score-factors-grid">
    `;

    factors.forEach(f => {
        html += `
            <div class="factor-item">
                <div class="factor-header">
                    <span>${escapeHtml(f.name)}</span>
                    <span style="color: #FDBA74;">${f.score}/${f.max}</span>
                </div>
                <div class="factor-desc">${escapeHtml(f.description)}</div>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>

        <!-- Budget & Financial Intelligence Panel -->
        <div class="budget-intelligence-panel">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-solid fa-calculator" style="color: var(--primary);"></i> Dynamic Budget Intelligence Engine</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Real-time cost rollup across activities, accommodations, flights, and logistics.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="openAddExpenseModal(${trip.id})">
                    <i class="fa-solid fa-receipt"></i> + Add Expense Item
                </button>
            </div>

            <!-- Financial KPIs -->
            <div class="budget-stats-grid">
                <div class="budget-metric-box">
                    <div class="label">Target Budget</div>
                    <div class="value" style="color: var(--primary);">${formatCurrency(trip.total_budget, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Total Estimated</div>
                    <div class="value" style="color: ${trip.total_estimated_cost > trip.total_budget ? 'var(--danger)' : 'var(--text-main)'};">${formatCurrency(trip.total_estimated_cost, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Remaining Budget</div>
                    <div class="value" style="color: ${trip.remaining_budget < 0 ? 'var(--danger)' : 'var(--success)'};">${formatCurrency(trip.remaining_budget, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Per Traveler</div>
                    <div class="value">${formatCurrency(trip.cost_per_traveler, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Per Day</div>
                    <div class="value">${formatCurrency(trip.cost_per_day, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Utilization</div>
                    <div class="value" style="color: ${util > 100 ? 'var(--danger)' : 'var(--accent)'};">${util.toFixed(0)}%</div>
                </div>
            </div>

            <!-- Rule-Based Intelligence Alerts -->
            <div style="margin-bottom: 2rem;">
                <h4 style="margin-bottom: 0.75rem; font-size: 1.05rem;">Intelligence Insights &amp; Pacing Warnings</h4>
    `;

    if (alerts.length === 0) {
        html += `
            <div class="intelligence-alert success">
                <i class="fa-solid fa-circle-check"></i>
                <div><strong>Healthy Itinerary:</strong> Your schedule and expenses are currently balanced and within budget parameters.</div>
            </div>
        `;
    } else {
        alerts.forEach(a => {
            let icon = 'fa-circle-info';
            if (a.type === 'warning') icon = 'fa-triangle-exclamation';
            if (a.type === 'success') icon = 'fa-circle-check';

            html += `
                <div class="intelligence-alert ${a.type}">
                    <i class="fa-solid ${icon}"></i>
                    <div>
                        <strong>${escapeHtml(a.title)}:</strong> ${escapeHtml(a.message)}
                    </div>
                </div>
            `;
        });
    }

    html += `
            </div>

            <!-- Category Cost Breakdown -->
            <div style="margin-bottom: 2rem;">
                <h4 style="margin-bottom: 1rem; font-size: 1.05rem;">Cost Allocation by Category</h4>
                <div style="display: flex; flex-direction: column; gap: 0.85rem;">
    `;

    const totalCost = trip.total_estimated_cost || 1;
    const catList = [
        { key: 'activities', label: 'Activities & Experiences', icon: 'fa-ticket', color: '#4F46E5', amount: bd.activities || 0 },
        { key: 'accommodation', label: 'Accommodation & Lodging', icon: 'fa-hotel', color: '#F97316', amount: bd.accommodation || 0 },
        { key: 'transportation', label: 'Transportation & Flights', icon: 'fa-plane', color: '#0EA5E9', amount: bd.transportation || 0 },
        { key: 'food', label: 'Food & Dining', icon: 'fa-utensils', color: '#10B981', amount: bd.food || 0 },
        { key: 'miscellaneous', label: 'Miscellaneous & Shopping', icon: 'fa-bag-shopping', color: '#8B5CF6', amount: bd.miscellaneous || 0 }
    ];

    catList.forEach(c => {
        const pct = ((c.amount / totalCost) * 100) || 0;
        html += `
            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 600; margin-bottom: 0.35rem;">
                    <span><i class="fa-solid ${c.icon}" style="color: ${c.color}; margin-right: 0.4rem;"></i> ${c.label}</span>
                    <span>${formatCurrency(c.amount, trip.currency)} (${pct.toFixed(0)}%)</span>
                </div>
                <div class="progress-bar-track">
                    <div class="progress-bar-fill" style="width: ${pct}%; background: ${c.color};"></div>
                </div>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <!-- Expenses List Table -->
            <div>
                <div class="section-header">
                    <h4 style="font-size: 1.05rem;">Recorded Logistics &amp; Expenses</h4>
                </div>
    `;

    if (expenses.length === 0) {
        html += `
            <div style="padding: 1.5rem; text-align: center; color: var(--text-muted); background: var(--bg-main); border-radius: var(--radius-md);">
                No standalone expenses added yet. Click <strong>+ Add Expense Item</strong> to log hotel bookings, flights, and meals.
            </div>
        `;
    } else {
        html += `
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
        `;
        expenses.forEach(e => {
            html += `
                <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem 1.25rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; font-size: 0.95rem;">${escapeHtml(e.name)}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 0.75rem; margin-top: 0.15rem;">
                            <span class="category-tag ${e.category}">${escapeHtml(e.category)}</span>
                            ${e.date ? `<span><i class="fa-regular fa-calendar"></i> ${e.date}</span>` : ''}
                            ${e.notes ? `<span>${escapeHtml(e.notes)}</span>` : ''}
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="font-family: var(--font-heading); font-weight: 700; font-size: 1.05rem;">${formatCurrency(e.amount, trip.currency)}</span>
                        <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteExpense(${trip.id}, ${e.id})"><i class="fa-regular fa-trash-can"></i></button>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    html += `
            </div>
        </div>
    `;

    return html;
}

// ================= Builder Sub-View: Calendar Grid =================
function renderCalendarGridView(trip) {
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div class="calendar-view-container">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-regular fa-calendar-days" style="color: var(--primary);"></i> Calendar Schedule Grid</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Visual day-by-day itinerary mapping.</p>
                </div>
            </div>
            <div class="calendar-grid">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);
        const dayCost = dayActs.reduce((sum, a) => sum + Number(a.estimated_cost || 0), 0);

        html += `
            <div class="calendar-day-cell">
                <div class="cal-day-title">
                    <span>Day ${dayNum}</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">${dayDateStr}</span>
                </div>
                <div style="flex: 1; overflow-y: auto;">
        `;

        if (dayActs.length === 0) {
            html += `<div style="font-size: 0.78rem; color: var(--text-light); text-align: center; margin-top: 2rem;">No events</div>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div class="cal-act-pill" title="${escapeHtml(a.name)}">
                        <span><strong>${escapeHtml(a.scheduled_time || '10:00')}</strong> ${escapeHtml(a.name.substring(0, 16))}...</span>
                        <span style="color: var(--primary);">${formatCurrency(a.estimated_cost, trip.currency)}</span>
                    </div>
                `;
            });
        }

        html += `
                </div>
                <div style="margin-top: auto; padding-top: 0.5rem; border-top: 1px dashed var(--border-color); font-size: 0.78rem; font-weight: 700; display: flex; justify-content: space-between;">
                    <span>Total:</span>
                    <span>${formatCurrency(dayCost, trip.currency)}</span>
                </div>
            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;
    return html;
}

// ================= Builder Sub-View: Vertical Timeline =================
function renderVerticalTimelineView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div class="calendar-view-container">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-solid fa-route" style="color: var(--primary);"></i> Journey Progression Timeline</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Step-by-step traveler journey sequence.</p>
                </div>
            </div>
            <div class="timeline-container">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
        } catch(e) {}

        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);

        html += `
            <div class="timeline-node">
                <div class="timeline-dot"><i class="fa-solid fa-flag"></i></div>
                <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
                        <span class="day-pill">DAY ${dayNum}</span>
                        <span style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">${dayDateStr}</span>
                    </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-muted);">Leisure day / Transit</p>`;
        } else {
            html += `<div style="display: flex; flex-direction: column; gap: 0.65rem;">`;
            dayActs.forEach(a => {
                html += `
                    <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem 1rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: var(--primary); margin-right: 0.5rem;">${escapeHtml(a.scheduled_time || '10:00')}</span>
                            <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                            <span class="category-tag ${a.category}" style="margin-left: 0.5rem;">${escapeHtml(a.category)}</span>
                        </div>
                        <span style="font-weight: 700; font-family: var(--font-heading);">${formatCurrency(a.estimated_cost, trip.currency)}</span>
                    </div>
                `;
            });
            html += `</div>`;
        }

        html += `
                </div>
            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;
    return html;
}

// ================= Builder Sub-View: Presentation Mode =================
function renderPresentationView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-xl); margin-bottom: 2rem;">
            <!-- Hero Banner -->
            <div style="height: 300px; position: relative; background: #1E1B4B;">
                <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80'}" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.75;">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 2rem; background: linear-gradient(to top, rgba(15, 23, 42, 0.95), transparent); color: #fff;">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span class="badge-chip accent">${trip.travel_style || 'Balanced'}</span>
                        <span class="badge-chip score"><i class="fa-solid fa-star"></i> Score: ${trip.trip_balance_score}/100</span>
                    </div>
                    <h1 style="color: #fff; font-size: 2.4rem; margin-bottom: 0.4rem;">${escapeHtml(trip.name)}</h1>
                    <div style="color: #C7D2FE; font-size: 1rem; display: flex; gap: 1.5rem; flex-wrap: wrap;">
                        <span><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span><i class="fa-solid fa-users"></i> ${trip.travelers_count} Travelers</span>
                        <span><i class="fa-solid fa-wallet"></i> Est. Cost: ${formatCurrency(trip.total_estimated_cost, trip.currency)}</span>
                    </div>
                </div>
            </div>

            <!-- Route Summary -->
            <div style="padding: 2rem; border-bottom: 1px solid var(--border-color); background: var(--bg-main);">
                <h3 style="margin-bottom: 1rem; font-size: 1.2rem;"><i class="fa-solid fa-map-pin" style="color: var(--primary);"></i> Route Overview</h3>
                <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
    `;

    stops.forEach((s, idx) => {
        html += `
            <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1.25rem; font-weight: 700;">
                ${idx + 1}. ${escapeHtml(s.city_name)}, ${escapeHtml(s.country_name)} (${s.duration_days}d)
            </div>
        `;
        if (idx < stops.length - 1) {
            html += `<i class="fa-solid fa-arrow-right" style="color: var(--primary);"></i>`;
        }
    });

    html += `
                </div>
            </div>

            <!-- Day-by-Day Showcase -->
            <div style="padding: 2rem;">
                <h3 style="margin-bottom: 1.5rem; font-size: 1.3rem;">Complete Day-by-Day Itinerary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        html += `
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
                    <span class="day-pill">DAY ${dayNum}</span>
                    <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted);">${dayDateStr}</span>
                </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-light); text-align: center; padding: 1rem 0;">Free exploration day</p>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div style="margin-bottom: 0.65rem; font-size: 0.88rem;">
                        <span style="font-weight: 700; color: var(--primary);">${escapeHtml(a.scheduled_time || '10:00')}</span> — 
                        <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                        <div style="font-size: 0.78rem; color: var(--text-muted);">${formatCurrency(a.estimated_cost, trip.currency)} &bull; ${escapeHtml(a.category)}</div>
                    </div>
                `;
            });
        }

        html += `</div>`;
    }

    html += `
                </div>
            </div>
        </div>
    `;

    return html;
}

// ================= View 4: Public Shared Trip Viewer =================
async function renderPublicSharedTrip() {
    const main = document.getElementById('main-content');
    if (!state.sharedToken) {
        // extract from URL if format is /shared/<token>
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'shared' && pathParts[2]) {
            state.sharedToken = pathParts[2];
        }
    }

    if (!state.sharedToken) {
        navigateTo('dashboard');
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading shared itinerary...</div>`;
    const res = await apiRequest(`/api/v1/shared/${state.sharedToken}`);
    if (!res.success || !res.trip) {
        main.innerHTML = `
            <div style="background: #fff; border-radius: var(--radius-lg); padding: 3rem; text-align: center; border: 1px solid var(--border-color);">
                <i class="fa-solid fa-link-slash" style="font-size: 3rem; color: var(--danger); margin-bottom: 1rem;"></i>
                <h2>Itinerary Not Available</h2>
                <p style="color: var(--text-muted); margin: 0.5rem 0 1.5rem;">This public link is either invalid, expired, or was made private by the author.</p>
                <button class="btn btn-primary" onclick="navigateTo('dashboard')">Go to GlobeTrotter Home</button>
            </div>
        `;
        return;
    }

    const trip = res.trip;
    state.sharedTrip = trip;

    let html = `
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-xl); margin-bottom: 2rem;">
            <!-- Top Callout Banner -->
            <div style="background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%); color: #fff; padding: 1.25rem 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <i class="fa-solid fa-share-nodes" style="font-size: 1.3rem; color: #FDBA74;"></i>
                    <div>
                        <div style="font-weight: 700;">Shared Itinerary by ${escapeHtml(trip.owner_name || 'GlobeTrotter Traveler')}</div>
                        <div style="font-size: 0.8rem; color: #C7D2FE;">You can copy this complete trip plan directly into your account.</div>
                    </div>
                </div>
                <button class="btn btn-accent btn-glow" onclick="handleCopySharedTrip('${state.sharedToken}')">
                    <i class="fa-solid fa-copy"></i> Copy Trip to My Account
                </button>
            </div>

            <!-- Hero Section -->
            <div style="height: 280px; position: relative;">
                <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80'}" style="width: 100%; height: 100%; object-fit: cover;">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 2rem; background: linear-gradient(to top, rgba(15, 23, 42, 0.9), transparent); color: #fff;">
                    <h1 style="color: #fff; font-size: 2.2rem; margin-bottom: 0.3rem;">${escapeHtml(trip.name)}</h1>
                    <div style="color: #C7D2FE; font-size: 0.95rem; display: flex; gap: 1.5rem; flex-wrap: wrap;">
                        <span><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span><i class="fa-solid fa-users"></i> ${trip.travelers_count} Traveler(s)</span>
                        ${trip.total_budget > 0 ? `<span><i class="fa-solid fa-wallet"></i> Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>` : ''}
                    </div>
                </div>
            </div>

            <!-- Day-by-Day Breakdown -->
            <div style="padding: 2rem;">
                <h3 style="margin-bottom: 1.5rem; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check" style="color: var(--primary);"></i> Trip Itinerary Schedule</h3>
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
    `;

    for (let dayNum = 1; dayNum <= (trip.duration_days || 1); dayNum++) {
        const dayActs = (trip.activities || []).filter(a => Number(a.day_number) === dayNum);

        html += `
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                    <span class="day-pill">DAY ${dayNum}</span>
                </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-muted);">Free leisure day</p>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: var(--primary); margin-right: 0.5rem;">${escapeHtml(a.scheduled_time || '10:00')}</span>
                            <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                            <span class="category-tag ${a.category}" style="margin-left: 0.5rem;">${escapeHtml(a.category)}</span>
                        </div>
                        ${a.estimated_cost > 0 ? `<span style="font-weight: 700;">${formatCurrency(a.estimated_cost, trip.currency)}</span>` : ''}
                    </div>
                `;
            });
        }

        html += `</div>`;
    }

    html += `
                </div>
            </div>
        </div>
    `;

    main.innerHTML = html;
}

// ================= View 5: Destinations Discovery =================
async function renderDestinationsCatalog() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading destination catalog...</div>`;

    const res = await apiRequest(`/api/v1/destinations?q=${encodeURIComponent(state.searchQuery)}&region=${state.selectedRegion}`);
    const destinations = res.success ? (res.destinations || []) : [];
    state.destinations = destinations;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">Explore Destinations</h1>
                <p style="color: var(--text-muted);">Discover top world destinations, curated activities, and estimated cost indexes.</p>
            </div>
        </div>

        <!-- Search and Region Filters -->
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem; margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
            <div style="flex: 1; min-width: 260px; position: relative;">
                <input type="text" id="dest-search-input" class="form-control" placeholder="Search cities, countries (e.g. Jaipur, France, Tokyo)..." value="${escapeHtml(state.searchQuery)}" onkeyup="handleDestSearch(event)">
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button class="btn btn-sm ${state.selectedRegion === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('all')">All Regions</button>
                <button class="btn btn-sm ${state.selectedRegion === 'asia' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('asia')">Asia</button>
                <button class="btn btn-sm ${state.selectedRegion === 'europe' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('europe')">Europe</button>
                <button class="btn btn-sm ${state.selectedRegion === 'middle_east' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('middle_east')">Middle East</button>
            </div>
        </div>

        <div class="trip-grid">
    `;

    if (destinations.length === 0) {
        html += `
            <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; background: #fff; border-radius: var(--radius-lg); border: 1px dashed var(--border-color);">
                <h3>No destinations matched your criteria.</h3>
                <p style="color: var(--text-muted); margin-top: 0.5rem;">Try searching for another city or country name.</p>
            </div>
        `;
    } else {
        destinations.forEach(dest => {
            html += `
                <div class="trip-card" onclick="openDestinationDetailModal(${dest.id})">
                    <div class="trip-card-cover">
                        <img src="${dest.cover_image}" alt="${escapeHtml(dest.name)}" loading="lazy">
                        <span class="trip-status-tag" style="background: rgba(15, 23, 42, 0.85); color: #FDBA74;">
                            <i class="fa-solid fa-star"></i> ${dest.popularity}/100
                        </span>
                        <span class="trip-style-tag">${escapeHtml(dest.country)}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h3>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                            ${escapeHtml(dest.description.substring(0, 110))}...
                        </p>
                        <div class="trip-meta-row" style="margin-top: auto;">
                            <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Rec: ${dest.recommended_duration_days} Days</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost Index: ${'₹'.repeat(dest.cost_index || 2)}</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${dest.activity_count || 0} Acts</div>
                        </div>
                        <div class="trip-card-actions">
                            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openAddToTripModal(${dest.id})">
                                <i class="fa-solid fa-plus"></i> Add to My Trip
                            </button>
                            <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openDestinationDetailModal(${dest.id})">
                                Details &amp; Experiences
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
    }

    html += `</div>`;
    main.innerHTML = html;
}

function handleDestSearch(e) {
    state.searchQuery = e.target.value;
    if (e.key === 'Enter') {
        renderDestinationsCatalog();
    }
}

function filterDestRegion(region) {
    state.selectedRegion = region;
    renderDestinationsCatalog();
}

// ================= View 6: Activities Catalog =================
async function renderActivitiesCatalog() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading experiences &amp; activities...</div>`;

    const res = await apiRequest(`/api/v1/activities?category=${state.selectedCategory}`);
    const activities = res.success ? (res.activities || []) : [];
    state.activities = activities;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">Experiences &amp; Activities</h1>
                <p style="color: var(--text-muted);">Browse curated things to do, tours, gastronomy, and cultural adventures.</p>
            </div>
        </div>

        <!-- Category Filters -->
        <div style="display: flex; gap: 0.4rem; margin-bottom: 2rem; flex-wrap: wrap;">
            <button class="btn btn-sm ${state.selectedCategory === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('all')">All Categories</button>
            <button class="btn btn-sm ${state.selectedCategory === 'sightseeing' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('sightseeing')">Sightseeing</button>
            <button class="btn btn-sm ${state.selectedCategory === 'food' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('food')">Food &amp; Dining</button>
            <button class="btn btn-sm ${state.selectedCategory === 'culture' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('culture')">Culture</button>
            <button class="btn btn-sm ${state.selectedCategory === 'adventure' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('adventure')">Adventure</button>
            <button class="btn btn-sm ${state.selectedCategory === 'nature' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('nature')">Nature</button>
            <button class="btn btn-sm ${state.selectedCategory === 'relaxation' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('relaxation')">Relaxation</button>
        </div>

        <div class="trip-grid">
    `;

    activities.forEach(act => {
        html += `
            <div class="trip-card">
                <div class="trip-card-cover" style="height: 150px;">
                    <img src="${act.image || 'https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(act.name)}" loading="lazy">
                    <span class="trip-status-tag ${act.category}">${escapeHtml(act.category)}</span>
                </div>
                <div class="trip-card-body">
                    <h3 class="trip-card-title">${escapeHtml(act.name)}</h3>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                        <i class="fa-solid fa-location-dot"></i> ${escapeHtml(act.city_name)}, ${escapeHtml(act.country_name)}
                    </div>
                    <p style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                        ${escapeHtml(act.description)}
                    </p>
                    <div class="trip-meta-row" style="margin-top: auto;">
                        <div class="trip-meta-item"><i class="fa-regular fa-clock"></i> ${act.duration_hours}h</div>
                        <div class="trip-meta-item"><i class="fa-solid fa-star" style="color: #F59E0B;"></i> ${act.popularity}/100</div>
                    </div>
                    <div class="trip-card-actions">
                        <span style="font-family: var(--font-heading); font-weight: 700; font-size: 1.1rem; color: var(--primary);">
                            ${formatCurrency(act.estimated_cost, 'INR')}
                        </span>
                        <button class="btn btn-primary btn-sm" onclick="openScheduleCatalogActModal(${act.id})">
                            <i class="fa-solid fa-plus"></i> Schedule to Trip
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    main.innerHTML = html;
}

function filterActivityCat(cat) {
    state.selectedCategory = cat;
    renderActivitiesCatalog();
}

// ================= View 7: Admin Analytics & User Management =================
async function renderAdminDashboard() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading platform analytics & users...</div>`;

    const [aRes, uRes] = await Promise.all([
        apiRequest('/api/v1/admin/analytics'),
        apiRequest('/api/v1/admin/users')
    ]);

    if (!aRes.success || !aRes.analytics) {
        main.innerHTML = `<div style="padding: 2rem; text-align: center;"><h3>Admin Access Denied</h3></div>`;
        return;
    }

    const a = aRes.analytics;
    const users = (uRes.success && uRes.users) ? uRes.users : [];

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;"><i class="fa-solid fa-chart-line" style="color: var(--primary);"></i> Platform Intelligence &amp; Analytics</h1>
                <p style="color: var(--text-muted);">Real-time adoption metrics, demand leaderboard, and traveler management.</p>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon-wrap indigo"><i class="fa-solid fa-users"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Registered Travelers</span>
                    <span class="kpi-val">${a.total_users}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap emerald"><i class="fa-solid fa-map"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Itineraries</span>
                    <span class="kpi-val">${a.total_trips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap amber"><i class="fa-solid fa-money-bill-wave"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Average Trip Budget</span>
                    <span class="kpi-val">${formatCurrency(a.avg_budget, 'INR')}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap sky"><i class="fa-solid fa-comments"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Community Stories</span>
                    <span class="kpi-val">${(a.community && a.community.total_posts) ? a.community.total_posts : 5}</span>
                </div>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
            <div class="admin-card">
                <h3 style="margin-bottom: 1rem;"><i class="fa-solid fa-trophy" style="color: var(--accent);"></i> Top Visited Destinations</h3>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
    `;

    (a.top_cities || []).forEach((c, idx) => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-subtle);">
                <span><strong>${idx + 1}. ${escapeHtml(c.name)}</strong>, ${escapeHtml(c.country)}</span>
                <span class="badge-chip primary">${c.visit_count} Itineraries</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <div class="admin-card">
                <h3 style="margin-bottom: 1rem;"><i class="fa-solid fa-chart-pie" style="color: var(--primary);"></i> Travel Style Distribution</h3>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
    `;

    (a.styles || []).forEach(s => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-subtle);">
                <span style="text-transform: capitalize;"><strong>${escapeHtml(s.travel_style)}</strong></span>
                <span class="badge-chip accent">${s.count} Trips</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>

        <!-- User Management Table -->
        <div class="admin-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3><i class="fa-solid fa-user-shield" style="color: var(--primary);"></i> Registered Users &amp; Profiles</h3>
                <span class="badge-chip primary">${users.length} Users</span>
            </div>
            <div style="overflow-x: auto;">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Location</th>
                            <th>Style</th>
                            <th>Currency</th>
                            <th>Trips</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map(u => `
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 0.6rem;">
                                        <div class="user-avatar" style="width: 32px; height: 32px; font-size: 0.85rem;">${escapeHtml(u.name.charAt(0).toUpperCase())}</div>
                                        <strong>${escapeHtml(u.name)}</strong>
                                    </div>
                                </td>
                                <td>${escapeHtml(u.email)}</td>
                                <td><span class="role-badge" style="${u.role === 'admin' ? 'background: #FEE2E2; color: #991B1B;' : ''}">${u.role}</span></td>
                                <td>${escapeHtml(u.city || '')}${u.country ? `, ${escapeHtml(u.country)}` : '-'}</td>
                                <td><span class="badge-chip" style="text-transform: capitalize;">${escapeHtml(u.preferred_travel_style || 'balanced')}</span></td>
                                <td>${escapeHtml(u.preferred_currency || 'INR')}</td>
                                <td><strong>${u.trips_count || 0}</strong></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    main.innerHTML = html;
}

// ================= View 8: Community Hub =================
let communityFilterContext = {
    search: '',
    city: 'all',
    style: 'all',
    sort: 'popular'
};

async function renderCommunityHub(search = '', city = 'all', style = 'all', sort = 'popular') {
    communityFilterContext.search = search;
    communityFilterContext.city = city;
    communityFilterContext.style = style;
    communityFilterContext.sort = sort;

    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading community itineraries & stories...</div>`;

    const queryParams = new URLSearchParams();
    if (search) queryParams.set('q', search);
    if (city !== 'all') queryParams.set('city', city);
    if (style !== 'all') queryParams.set('style', style);
    if (sort) queryParams.set('sort_by', sort);

    const res = await apiRequest(`/api/v1/community/posts?${queryParams.toString()}`);
    const posts = res.success ? (res.posts || []) : [];

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;"><i class="fa-solid fa-users" style="color: var(--primary);"></i> GlobeTrotter Community Hub</h1>
                <p style="color: var(--text-muted);">Explore real traveler stories, like &amp; save inspirations, and 1-click import itineraries directly into your trip.</p>
            </div>
            <button class="btn btn-primary btn-glow" onclick="openCreateCommunityPostModal()">
                <i class="fa-solid fa-pen-nib"></i> <span>Share Your Experience</span>
            </button>
        </div>

        <!-- Community Filter Controls -->
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem; margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
            <div style="flex: 1; min-width: 240px;">
                <input type="text" id="comm-search-input" class="form-control" placeholder="Search stories, forts, temples, food..." value="${escapeHtml(search)}" onkeyup="if(event.key==='Enter') renderCommunityHub(this.value, communityFilterContext.city, communityFilterContext.style, communityFilterContext.sort)">
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <select id="comm-sort-select" class="form-control" style="width: auto;" onchange="renderCommunityHub(communityFilterContext.search, communityFilterContext.city, communityFilterContext.style, this.value)">
                    <option value="popular" ${sort === 'popular' ? 'selected' : ''}>🔥 Most Popular</option>
                    <option value="rating" ${sort === 'rating' ? 'selected' : ''}>⭐ Highest Rated</option>
                    <option value="newest" ${sort === 'newest' ? 'selected' : ''}>✨ Newest First</option>
                    <option value="imports" ${sort === 'imports' ? 'selected' : ''}>📥 Most Imported</option>
                </select>
                <button class="btn btn-primary btn-sm" onclick="renderCommunityHub(document.getElementById('comm-search-input').value, communityFilterContext.city, communityFilterContext.style, communityFilterContext.sort)">
                    <i class="fa-solid fa-magnifying-glass"></i> Filter
                </button>
            </div>
        </div>
    `;

    if (posts.length === 0) {
        html += `
            <div style="background: #fff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); padding: 3.5rem; text-align: center;">
                <i class="fa-solid fa-compass" style="font-size: 3rem; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No community stories found</h3>
                <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Be the first to share your travel journey with the GlobeTrotter community!</p>
                <button class="btn btn-primary" onclick="openCreateCommunityPostModal()"><i class="fa-solid fa-pen-nib"></i> Share Experience</button>
            </div>
        `;
    } else {
        html += `<div class="community-grid">`;
        posts.forEach(post => {
            const hList = post.highlights || [];
            html += `
                <div class="community-post-card">
                    <div class="community-card-cover">
                        <img src="${post.cover_image || 'https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(post.title)}" loading="lazy">
                        <span class="trip-status-tag" style="background: rgba(15, 23, 42, 0.85); color: #FBBF24;">
                            <i class="fa-solid fa-star"></i> ${post.rating || 5.0}
                        </span>
                        <span class="trip-style-tag">${escapeHtml(post.travel_style || 'Adventure')}</span>
                    </div>
                    <div class="community-card-body">
                        <div class="community-author-row">
                            <img src="${post.author_avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80'}" class="community-author-avatar" alt="${escapeHtml(post.author_name)}">
                            <div>
                                <div class="community-author-name">${escapeHtml(post.author_name)}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(post.city_name || 'India')}</div>
                            </div>
                        </div>

                        <h3 class="community-post-title" onclick="openCommunityPostDetailModal(${post.id})" style="cursor: pointer;">
                            ${escapeHtml(post.title)}
                        </h3>
                        <p class="community-post-excerpt">${escapeHtml(post.content)}</p>

                        ${hList.length > 0 ? `
                            <div class="community-highlights-preview">
                                <h6><i class="fa-solid fa-list-check"></i> Featured Highlights (${hList.length})</h6>
                                <div>${escapeHtml(hList.slice(0, 2).map(h => h.name).join(' · '))}</div>
                            </div>
                        ` : ''}

                        <div class="community-card-footer">
                            <div class="community-reactions">
                                <button class="reaction-btn ${post.user_liked ? 'liked' : ''}" onclick="toggleCommunityLike(${post.id})">
                                    <i class="${post.user_liked ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
                                    <span id="post-likes-${post.id}">${post.likes_count || 0}</span>
                                </button>
                                <button class="reaction-btn ${post.user_saved ? 'saved' : ''}" onclick="toggleCommunitySave(${post.id})">
                                    <i class="${post.user_saved ? 'fa-solid' : 'fa-regular'} fa-bookmark"></i>
                                    <span id="post-saves-${post.id}">${post.saves_count || 0}</span>
                                </button>
                            </div>

                            <button class="btn btn-primary btn-sm" onclick="open1ClickImportModal(${post.id})">
                                <i class="fa-solid fa-download"></i> 1-Click Import
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    main.innerHTML = html;
}

// ================= Modals Management =================
function closeModal() {
    const container = document.getElementById('modal-container');
    if (container) container.innerHTML = '';
}

function openModal(contentHtml) {
    const container = document.getElementById('modal-container');
    if (!container) return;
    container.innerHTML = `
        <div class="modal-backdrop" onclick="if(event.target === this) closeModal()">
            <div class="modal-card">
                ${contentHtml}
            </div>
        </div>
    `;
}

// 1. Login Modal
function openLoginModal() {
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">Sign In to GlobeTrotter</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleLogin(document.getElementById('login-email').value, document.getElementById('login-pass').value);">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" id="login-email" class="form-control" required placeholder="demo@globetrotter.travel">
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" id="login-pass" class="form-control" required placeholder="••••••••">
                </div>
                <div style="background: var(--bg-subtle); padding: 0.85rem; border-radius: var(--radius-md); font-size: 0.85rem; margin-top: 1rem;">
                    <strong>Fast Hackathon Login:</strong>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                        <button type="button" class="btn btn-outline btn-sm" onclick="handleDemoLogin('traveler')">Demo Traveler</button>
                        <button type="button" class="btn btn-outline btn-sm" onclick="handleDemoLogin('admin')">Admin Demo</button>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="openSignupModal()">Create Account</button>
                <button type="submit" class="btn btn-primary">Sign In</button>
            </div>
        </form>
    `);
}

// 2. Signup Modal
function openSignupModal() {
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-user-plus" style="color: var(--primary);"></i> Create GlobeTrotter Account</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleSignupSubmit();">
            <div class="modal-body">
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">First Name *</label>
                        <input type="text" id="signup-first-name" class="form-control" required placeholder="e.g. Rohan">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Last Name</label>
                        <input type="text" id="signup-last-name" class="form-control" placeholder="e.g. Sharma">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Email Address *</label>
                        <input type="email" id="signup-email" class="form-control" required placeholder="rohan@example.com">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" id="signup-phone" class="form-control" placeholder="+91 98765 43210">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Password (min 6 chars) *</label>
                    <input type="password" id="signup-pass" class="form-control" minlength="6" required placeholder="••••••••">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">City</label>
                        <input type="text" id="signup-city" class="form-control" placeholder="e.g. Mumbai">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Country</label>
                        <input type="text" id="signup-country" class="form-control" placeholder="e.g. India">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Preferred Currency</label>
                        <select id="signup-curr" class="form-control">
                            <option value="INR" selected>₹ INR (Indian Rupee)</option>
                            <option value="USD">$ USD (US Dollar)</option>
                            <option value="EUR">€ EUR (Euro)</option>
                            <option value="GBP">£ GBP (British Pound)</option>
                            <option value="AED">AED (UAE Dirham)</option>
                            <option value="SGD">S$ (Singapore Dollar)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Primary Travel Style</label>
                        <select id="signup-style" class="form-control">
                            <option value="balanced" selected>Balanced Explorer</option>
                            <option value="budget">Budget Backpacker</option>
                            <option value="luxury">Luxury &amp; Comfort</option>
                            <option value="adventure">Active Adventure</option>
                            <option value="relaxed">Relaxed &amp; Slow Travel</option>
                            <option value="family">Family Friendly</option>
                            <option value="solo">Solo Wanderer</option>
                            <option value="business">Business &amp; Bleisure</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Profile Photo URL</label>
                    <input type="url" id="signup-avatar" class="form-control" placeholder="https://images.unsplash.com/photo-...">
                </div>
                <div class="form-group">
                    <label class="form-label">Travel Bio / Additional Notes</label>
                    <textarea id="signup-info" class="form-control" rows="2" placeholder="Passions, favorite destinations, bucket lists..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="openLoginModal()">Already have an account?</button>
                <button type="submit" class="btn btn-primary btn-glow">Create Account</button>
            </div>
        </form>
    `);
}

async function handleSignupSubmit() {
    const firstName = document.getElementById('signup-first-name').value.trim();
    const lastName = document.getElementById('signup-last-name').value.trim();
    const fullName = `${firstName} ${lastName}`.trim();
    const email = document.getElementById('signup-email').value.trim();
    const phone = document.getElementById('signup-phone').value.trim();
    const pass = document.getElementById('signup-pass').value;
    const city = document.getElementById('signup-city').value.trim();
    const country = document.getElementById('signup-country').value.trim();
    const currency = document.getElementById('signup-curr').value;
    const style = document.getElementById('signup-style').value;
    const avatar = document.getElementById('signup-avatar').value.trim();
    const info = document.getElementById('signup-info').value.trim();

    const res = await apiRequest('/api/v1/auth/signup', 'POST', {
        name: fullName,
        first_name: firstName,
        last_name: lastName,
        email: email,
        password: pass,
        phone: phone,
        city: city,
        country: country,
        preferred_currency: currency,
        preferred_travel_style: style,
        avatar_url: avatar,
        additional_info: info
    });

    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Welcome to GlobeTrotter, ${state.user.name}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Registration failed', 'error');
    }
}

// 3. Create Trip Modal
function openCreateTripModal() {
    if (!state.user) {
        openLoginModal();
        return;
    }

    // Default dates: tomorrow and +6 days
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const end = new Date();
    end.setDate(end.getDate() + 7);

    const startStr = tomorrow.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-compass" style="color: var(--primary);"></i> Plan a New Itinerary</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleCreateTripSubmit();">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Itinerary Title *</label>
                    <input type="text" id="trip-name" class="form-control" required placeholder="e.g. Rajasthan Explorer" value="Rajasthan Explorer">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Start Date *</label>
                        <input type="date" id="trip-start" class="form-control" required value="${startStr}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date *</label>
                        <input type="date" id="trip-end" class="form-control" required value="${endStr}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Total Target Budget (INR/Currency) *</label>
                        <input type="number" id="trip-budget" class="form-control" required min="0" value="35000" placeholder="35000">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Number of Travelers *</label>
                        <input type="number" id="trip-travelers" class="form-control" required min="1" value="2">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Currency</label>
                        <select id="trip-currency" class="form-control">
                            <option value="INR" selected>₹ INR (Indian Rupee)</option>
                            <option value="USD">$ USD (US Dollar)</option>
                            <option value="EUR">€ EUR (Euro)</option>
                            <option value="GBP">£ GBP (British Pound)</option>
                            <option value="AED">AED (UAE Dirham)</option>
                            <option value="SGD">S$ (Singapore Dollar)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="trip-style" class="form-control">
                            <option value="balanced" selected>Balanced Explorer</option>
                            <option value="budget">Budget Backpacker</option>
                            <option value="luxury">Luxury &amp; Comfort</option>
                            <option value="adventure">Active Adventure</option>
                            <option value="relaxed">Relaxed &amp; Slow Travel</option>
                            <option value="family">Family Friendly</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Cover Photo URL</label>
                    <input type="url" id="trip-cover" class="form-control" value="https://images.unsplash.com/photo-1603288967969-952467d027f6?auto=format&fit=crop&w=1200&q=80">
                </div>
                <div class="form-group">
                    <label class="form-label">Description / Travel Goals</label>
                    <textarea id="trip-desc" class="form-control" rows="2" placeholder="Highlights, personal expectations, notes...">Exploring historic forts, Rajasthani royal palaces, and authentic local cuisine across Delhi, Jaipur, and Udaipur.</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary btn-glow">Create &amp; Build Itinerary</button>
            </div>
        </form>
    `);
}

async function handleCreateTripSubmit() {
    const name = document.getElementById('trip-name').value.trim();
    const startDate = document.getElementById('trip-start').value;
    const endDate = document.getElementById('trip-end').value;
    const budget = parseFloat(document.getElementById('trip-budget').value) || 0;
    const travelers = parseInt(document.getElementById('trip-travelers').value) || 1;
    const currency = document.getElementById('trip-currency').value;
    const travelStyle = document.getElementById('trip-style').value;
    const cover = document.getElementById('trip-cover').value.trim();
    const desc = document.getElementById('trip-desc').value.trim();

    if (!name || !startDate || !endDate) {
        showToast('Please fill all required fields.', 'error');
        return;
    }
    if (endDate < startDate) {
        showToast('End date cannot be earlier than start date.', 'error');
        return;
    }

    const payload = {
        name,
        start_date: startDate,
        end_date: endDate,
        total_budget: budget,
        travelers_count: travelers,
        currency,
        travel_style: travelStyle,
        cover_image: cover,
        description: desc
    };

    const res = await apiRequest('/api/v1/trips', 'POST', payload);
    if (res.success && res.trip_id) {
        closeModal();
        showToast('Trip created! Loading Itinerary Builder...');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to create trip', 'error');
    }
}

// 4. Add Destination Stop Modal
function openAddStopModal(tripId) {
    if (!state.destinations || state.destinations.length === 0) {
        apiRequest('/api/v1/destinations').then(r => {
            state.destinations = r.destinations || [];
            showAddStopModalContent(tripId);
        });
    } else {
        showAddStopModalContent(tripId);
    }
}

function showAddStopModalContent(tripId) {
    const trip = state.currentTrip;
    let optHtml = state.destinations.map(d => `<option value="${d.id}">${escapeHtml(d.name)}, ${escapeHtml(d.country)}</option>`).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-map-location-dot" style="color: var(--primary);"></i> Add Destination Stop</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddStopSubmit(${tripId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Select City Destination *</label>
                    <select id="stop-city" class="form-control" required>
                        ${optHtml}
                    </select>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Arrival Date</label>
                        <input type="date" id="stop-arrival" class="form-control" value="${trip ? trip.start_date : ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Departure Date</label>
                        <input type="date" id="stop-departure" class="form-control" value="${trip ? trip.end_date : ''}">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Stop Notes &amp; Accommodation Details</label>
                    <textarea id="stop-notes" class="form-control" rows="2" placeholder="e.g. Hotel Heritage Haveli, booking ref #9823..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Stop</button>
            </div>
        </form>
    `);
}

async function handleAddStopSubmit(tripId) {
    const cityId = document.getElementById('stop-city').value;
    const arrivalDate = document.getElementById('stop-arrival').value;
    const departureDate = document.getElementById('stop-departure').value;
    const notes = document.getElementById('stop-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/stops`, 'POST', {
        city_id: cityId,
        arrival_date: arrivalDate,
        departure_date: departureDate,
        notes
    });

    if (res.success) {
        closeModal();
        showToast('Destination stop added!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to add stop', 'error');
    }
}

// 5. Add Activity & Section Modal (with curated catalog browser)
async function openAddActivityModal(tripId, defaultDay = 1) {
    const trip = state.currentTrip;
    const stops = trip ? trip.stops || [] : [];
    
    // Fetch activities for the current trip's destination stops
    const res = await apiRequest('/api/v1/activities');
    const catalogActs = res.success ? (res.activities || []) : [];

    let stopOptions = stops.map(s => `<option value="${s.id}">${escapeHtml(s.city_name)}</option>`).join('');
    if (!stopOptions) stopOptions = `<option value="">(No specific stop assigned)</option>`;

    let actCards = catalogActs.map(a => `
        <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div>
                <div style="font-weight: 700; font-size: 0.92rem;">${escapeHtml(a.name)}</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">
                    <span class="category-tag ${a.category}">${escapeHtml(a.category)}</span> &bull; ${escapeHtml(a.city_name)} &bull; ${formatCurrency(a.estimated_cost, trip ? trip.currency : 'INR')}
                </div>
            </div>
            <button type="button" class="btn btn-primary btn-sm" onclick="selectCatalogActivity(${a.id}, '${escapeHtml(a.name).replace(/'/g, "\\'")}', '${a.category}', ${a.duration_hours}, ${a.estimated_cost})">
                Select
            </button>
        </div>
    `).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-layer-group" style="color: var(--primary);"></i> Add Section to Day ${defaultDay}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddActivitySubmit(${tripId});">
            <div class="modal-body">
                <div style="margin-bottom: 1.25rem;">
                    <label class="form-label">Pick from Curated Experiences Catalog</label>
                    <div style="max-height: 150px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.5rem;">
                        ${actCards}
                    </div>
                </div>

                <div style="border-top: 1px solid var(--border-color); padding-top: 1rem;">
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Section / Activity Title *</label>
                            <input type="text" id="act-name" class="form-control" required placeholder="e.g. Amber Palace Sunset Tour">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Section Type *</label>
                            <select id="act-section-type" class="form-control">
                                <option value="activity" selected>🎯 Activity / Sight</option>
                                <option value="transport">🚆 Transit / Transport</option>
                                <option value="hotel">🏨 Hotel / Stay Check-in</option>
                                <option value="food">🍽️ Food / Dining</option>
                                <option value="event">🎭 Event / Performance</option>
                                <option value="free_time">☕ Free Time / Leisure</option>
                                <option value="custom">✨ Custom Item</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Day Number (1, 2, ...)</label>
                            <input type="number" id="act-day" class="form-control" required min="1" max="${trip ? trip.duration_days : 30}" value="${defaultDay}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Scheduled Time Slot</label>
                            <input type="text" id="act-time" class="form-control" value="10:00" placeholder="09:30, 14:00...">
                        </div>
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Category</label>
                            <select id="act-cat" class="form-control">
                                <option value="sightseeing">Sightseeing</option>
                                <option value="food">Food &amp; Dining</option>
                                <option value="culture">Culture &amp; History</option>
                                <option value="adventure">Adventure</option>
                                <option value="nature">Nature</option>
                                <option value="relaxation">Relaxation</option>
                                <option value="shopping">Shopping</option>
                                <option value="transport">Transit</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Estimated Cost (${trip ? trip.currency : 'INR'})</label>
                            <input type="number" id="act-cost" class="form-control" min="0" value="750">
                        </div>
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Duration (Hours)</label>
                            <input type="number" step="0.5" id="act-dur" class="form-control" value="2.5">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Associated Stop</label>
                            <select id="act-stop" class="form-control">
                                ${stopOptions}
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Location / Address</label>
                        <input type="text" id="act-location" class="form-control" placeholder="e.g. Devisinghpura, Amer, Jaipur, Rajasthan 302001">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Notes &amp; Booking Details</label>
                        <textarea id="act-notes" class="form-control" rows="2" placeholder="Entry passes, guide details, tickets..."></textarea>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Schedule Section</button>
            </div>
        </form>
    `);
}

function selectCatalogActivity(id, name, cat, dur, cost) {
    document.getElementById('act-name').value = name;
    document.getElementById('act-cat').value = cat;
    document.getElementById('act-dur').value = dur;
    document.getElementById('act-cost').value = cost;
}

async function handleAddActivitySubmit(tripId) {
    const name = document.getElementById('act-name').value.trim();
    const sectionType = document.getElementById('act-section-type').value;
    const dayNumber = parseInt(document.getElementById('act-day').value) || 1;
    const scheduledTime = document.getElementById('act-time').value.trim();
    const category = document.getElementById('act-cat').value;
    const estimatedCost = parseFloat(document.getElementById('act-cost').value) || 0;
    const durationHours = parseFloat(document.getElementById('act-dur').value) || 2.0;
    const stopId = document.getElementById('act-stop').value || null;
    const locationAddress = document.getElementById('act-location').value.trim();
    const notes = document.getElementById('act-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/activities`, 'POST', {
        name,
        section_type: sectionType,
        day_number: dayNumber,
        scheduled_time: scheduledTime,
        category,
        estimated_cost: estimatedCost,
        duration_hours: durationHours,
        stop_id: stopId,
        location_address: locationAddress,
        notes: notes
    });

    if (res.success) {
        closeModal();
        showToast('Section added and budget recalculated!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to schedule activity', 'error');
    }
}

// 5b. Edit Activity & Section Modal
async function openEditActivityModal(tripId, actId) {
    const trip = state.currentTrip;
    if (!trip) return;
    const act = (trip.activities || []).find(a => a.id === actId);
    if (!act) {
        showToast('Activity not found', 'error');
        return;
    }

    const stops = trip.stops || [];
    let stopOptions = stops.map(s => `<option value="${s.id}" ${act.stop_id === s.id ? 'selected' : ''}>${escapeHtml(s.city_name)}</option>`).join('');
    if (!stopOptions) stopOptions = `<option value="">(No specific stop assigned)</option>`;

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-pen"></i> Edit Section: ${escapeHtml(act.name)}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleEditActivitySubmit(${tripId}, ${actId});">
            <div class="modal-body">
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Title *</label>
                        <input type="text" id="edit-act-name" class="form-control" required value="${escapeHtml(act.name)}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Section Type</label>
                        <select id="edit-act-section-type" class="form-control">
                            <option value="activity" ${act.section_type === 'activity' ? 'selected' : ''}>🎯 Activity / Sight</option>
                            <option value="transport" ${act.section_type === 'transport' ? 'selected' : ''}>🚆 Transit / Transport</option>
                            <option value="hotel" ${act.section_type === 'hotel' ? 'selected' : ''}>🏨 Hotel / Stay</option>
                            <option value="food" ${act.section_type === 'food' ? 'selected' : ''}>🍽️ Food / Dining</option>
                            <option value="event" ${act.section_type === 'event' ? 'selected' : ''}>🎭 Event / Performance</option>
                            <option value="free_time" ${act.section_type === 'free_time' ? 'selected' : ''}>☕ Free Time / Leisure</option>
                            <option value="custom" ${act.section_type === 'custom' ? 'selected' : ''}>✨ Custom Item</option>
                        </select>
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Day Number</label>
                        <input type="number" id="edit-act-day" class="form-control" required min="1" max="${trip.duration_days}" value="${act.day_number}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Scheduled Time</label>
                        <input type="text" id="edit-act-time" class="form-control" value="${escapeHtml(act.scheduled_time || '10:00')}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Category</label>
                        <select id="edit-act-cat" class="form-control">
                            <option value="sightseeing" ${act.category === 'sightseeing' ? 'selected' : ''}>Sightseeing</option>
                            <option value="food" ${act.category === 'food' ? 'selected' : ''}>Food &amp; Dining</option>
                            <option value="culture" ${act.category === 'culture' ? 'selected' : ''}>Culture &amp; History</option>
                            <option value="adventure" ${act.category === 'adventure' ? 'selected' : ''}>Adventure</option>
                            <option value="nature" ${act.category === 'nature' ? 'selected' : ''}>Nature</option>
                            <option value="relaxation" ${act.category === 'relaxation' ? 'selected' : ''}>Relaxation</option>
                            <option value="shopping" ${act.category === 'shopping' ? 'selected' : ''}>Shopping</option>
                            <option value="transport" ${act.category === 'transport' ? 'selected' : ''}>Transit</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Estimated Cost (${trip.currency})</label>
                        <input type="number" id="edit-act-cost" class="form-control" min="0" value="${act.estimated_cost}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Duration (Hours)</label>
                        <input type="number" step="0.5" id="edit-act-dur" class="form-control" value="${act.duration_hours}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Associated Stop</label>
                        <select id="edit-act-stop" class="form-control">
                            ${stopOptions}
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Location / Address</label>
                    <input type="text" id="edit-act-location" class="form-control" value="${escapeHtml(act.location_address || '')}">
                </div>
                <div class="form-group">
                    <label class="form-label">Notes &amp; Booking Details</label>
                    <textarea id="edit-act-notes" class="form-control" rows="2">${escapeHtml(act.notes || '')}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
        </form>
    `);
}

async function handleEditActivitySubmit(tripId, actId) {
    const name = document.getElementById('edit-act-name').value.trim();
    const sectionType = document.getElementById('edit-act-section-type').value;
    const dayNumber = parseInt(document.getElementById('edit-act-day').value) || 1;
    const scheduledTime = document.getElementById('edit-act-time').value.trim();
    const category = document.getElementById('edit-act-cat').value;
    const estimatedCost = parseFloat(document.getElementById('edit-act-cost').value) || 0;
    const durationHours = parseFloat(document.getElementById('edit-act-dur').value) || 2.0;
    const stopId = document.getElementById('edit-act-stop').value || null;
    const locationAddress = document.getElementById('edit-act-location').value.trim();
    const notes = document.getElementById('edit-act-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}`, 'PUT', {
        name,
        section_type: sectionType,
        day_number: dayNumber,
        scheduled_time: scheduledTime,
        category,
        estimated_cost: estimatedCost,
        duration_hours: durationHours,
        stop_id: stopId,
        location_address: locationAddress,
        notes: notes
    });

    if (res.success) {
        closeModal();
        showToast('Section updated!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to update section', 'error');
    }
}

// 5c. Move Activity to Another Day Modal
function openMoveActivityModal(tripId, actId, currentDay, maxDays) {
    let dayOptions = '';
    for (let d = 1; d <= maxDays; d++) {
        dayOptions += `<option value="${d}" ${d === currentDay ? 'selected' : ''}>Day ${d}</option>`;
    }

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-arrow-right-arrow-left"></i> Move Section to Another Day</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleMoveActivityDay(${tripId}, ${actId}, parseInt(document.getElementById('move-target-day').value));">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Select Target Itinerary Day</label>
                    <select id="move-target-day" class="form-control">
                        ${dayOptions}
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Move Section</button>
            </div>
        </form>
    `);
}

async function handleMoveActivityDay(tripId, actId, newDay) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}/move-day`, 'POST', { day_number: newDay });
    if (res.success) {
        closeModal();
        showToast(`Moved to Day ${newDay}!`);
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to move section', 'error');
    }
}

// 5d. Duplicate Activity Handler
async function handleDuplicateActivity(tripId, actId, targetDay = null) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}/duplicate`, 'POST', { target_day: targetDay });
    if (res.success) {
        showToast('Section cloned successfully!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to duplicate section', 'error');
    }
}

// 5e. Smart Balancing 1-Click Execution
async function handleAcceptBalancing(tripId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/balance`, 'POST');
    if (res.success) {
        showToast(res.message || 'Itinerary schedule rebalanced smoothly across available days!', 'success');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to rebalance itinerary', 'error');
    }
}

// 5f. Delete Activity Handler
async function handleDeleteActivity(tripId, actId) {
    if (!confirm('Are you sure you want to remove this scheduled item?')) return;
    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}`, 'DELETE');
    if (res.success) {
        showToast('Item removed.');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to remove item', 'error');
    }
}

// 6. Add Expense Modal
function openAddExpenseModal(tripId) {
    const trip = state.currentTrip;
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-receipt" style="color: var(--primary);"></i> Log Trip Expense / Logistic</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddExpenseSubmit(${tripId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Expense Description *</label>
                    <input type="text" id="exp-name" class="form-control" required placeholder="e.g. Flight Delhi to Jaipur, Heritage Hotel Stay...">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Category *</label>
                        <select id="exp-cat" class="form-control" required>
                            <option value="accommodation">Accommodation / Hotel</option>
                            <option value="transportation">Transportation / Flights / Trains</option>
                            <option value="food">Food &amp; Dining</option>
                            <option value="activities">Activities &amp; Tours</option>
                            <option value="miscellaneous">Miscellaneous / Visa</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Amount (${trip ? trip.currency : 'INR'}) *</label>
                        <input type="number" id="exp-amount" class="form-control" required min="0" value="2500">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Notes / Booking Confirmation Code</label>
                    <input type="text" id="exp-notes" class="form-control" placeholder="Booking Ref: PNR-98124">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Expense</button>
            </div>
        </form>
    `);
}

async function handleAddExpenseSubmit(tripId) {
    const name = document.getElementById('exp-name').value.trim();
    const category = document.getElementById('exp-cat').value;
    const amount = parseFloat(document.getElementById('exp-amount').value) || 0;
    const notes = document.getElementById('exp-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/expenses`, 'POST', {
        name, category, amount, notes
    });

    if (res.success) {
        closeModal();
        showToast('Expense recorded & budget updated!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to record expense', 'error');
    }
}

// 7. Share Itinerary Modal
async function openShareModal(tripId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/share`, 'POST', { is_public: true, share_budget: true });
    if (!res.success) {
        showToast(res.error || 'Failed to generate share link', 'error');
        return;
    }

    const fullShareUrl = `${window.location.origin}/shared/${res.share_token}`;

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-share-nodes" style="color: var(--primary);"></i> Share Itinerary Publicly</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.25rem;">
                Anyone with this secure link can view your itinerary and copy it directly to their own account.
            </p>
            <div class="form-group">
                <label class="form-label">Secure Public Link</label>
                <div style="display: flex; gap: 0.5rem;">
                    <input type="text" id="share-link-input" class="form-control" readonly value="${fullShareUrl}">
                    <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${fullShareUrl}'); showToast('Share link copied to clipboard!');">
                        <i class="fa-regular fa-copy"></i> Copy
                    </button>
                </div>
            </div>
            <div style="background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md); font-size: 0.88rem; display: flex; align-items: center; justify-content: space-between;">
                <span>Include budget breakdown in public view</span>
                <input type="checkbox" checked onchange="toggleShareBudget(${tripId}, this.checked)" style="width: 18px; height: 18px;">
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="window.open('${fullShareUrl}', '_blank')">
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Public View
            </button>
            <button class="btn btn-primary" onclick="closeModal()">Done</button>
        </div>
    `);
}

async function toggleShareBudget(tripId, includeBudget) {
    await apiRequest(`/api/v1/trips/${tripId}/share`, 'POST', { is_public: true, share_budget: includeBudget });
    showToast(`Public budget view ${includeBudget ? 'enabled' : 'hidden'}.`);
}

// 8. Reorder Stops Handler
async function handleMoveStop(tripId, currentIndex, direction) {
    const trip = state.currentTrip;
    if (!trip || !trip.stops) return;

    const stops = [...trip.stops];
    const targetIndex = currentIndex + direction;
    if (targetIndex < 0 || targetIndex >= stops.length) return;

    // Swap
    const temp = stops[currentIndex];
    stops[currentIndex] = stops[targetIndex];
    stops[targetIndex] = temp;

    const stopIds = stops.map(s => s.id);
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops/reorder`, 'POST', { stop_ids: stopIds });
    if (res.success) {
        showToast('Route reordered!');
        renderItineraryBuilder();
    }
}

// 9. Duplicate Trip Handler
async function handleDuplicateTrip(tripId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/duplicate`, 'POST');
    if (res.success && res.trip_id) {
        showToast('Itinerary duplicated into your account!');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to duplicate trip', 'error');
    }
}

// 10. Copy Shared Trip Handler
async function handleCopySharedTrip(token) {
    if (!state.user) {
        showToast('Please sign in or use 1-click demo login to copy this trip.', 'info');
        openLoginModal();
        return;
    }

    const res = await apiRequest(`/api/v1/shared/${token}/copy`, 'POST');
    if (res.success && res.trip_id) {
        showToast('Itinerary cloned into your account!');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to copy trip', 'error');
    }
}

// 11. Delete Trip Handler
async function handleDeleteTrip(tripId) {
    if (!confirm("Are you sure you want to delete this trip? All stops and scheduled activities will be permanently removed.")) {
        return;
    }
    const res = await apiRequest(`/api/v1/trips/${tripId}`, 'DELETE');
    if (res.success) {
        showToast('Trip deleted.');
        navigateTo('trips');
    } else {
        showToast(res.error || 'Failed to delete trip', 'error');
    }
}

// 12. Delete Stop & Activity Handlers
async function handleDeleteStop(tripId, stopId) {
    if (!confirm("Remove this destination stop and its activities from the trip?")) return;
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops/${stopId}`, 'DELETE');
    if (res.success) {
        showToast('Stop removed.');
        renderItineraryBuilder();
    }
}

async function handleDeleteActivity(tripId, actId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}`, 'DELETE');
    if (res.success) {
        showToast('Activity removed.');
        renderItineraryBuilder();
    }
}

async function handleDeleteExpense(tripId, expId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/expenses/${expId}`, 'DELETE');
    if (res.success) {
        showToast('Expense removed.');
        renderItineraryBuilder();
    }
}

// 13. Destination Detail Modal
async function openDestinationDetailModal(cityId) {
    const res = await apiRequest(`/api/v1/destinations/${cityId}`);
    if (!res.success || !res.destination) return;

    const dest = res.destination;
    const activities = dest.activities || [];

    let actsHtml = activities.map(a => `
        <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 700;">${escapeHtml(a.name)}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">
                    <span class="category-tag ${a.category}">${escapeHtml(a.category)}</span> &bull; ${a.duration_hours}h
                </div>
            </div>
            <span style="font-weight: 700; color: var(--primary);">${formatCurrency(a.estimated_cost, 'INR')}</span>
        </div>
    `).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <img src="${dest.cover_image}" style="width: 100%; height: 200px; object-fit: cover; border-radius: var(--radius-md); margin-bottom: 1rem;">
            <p style="color: var(--text-main); line-height: 1.6; margin-bottom: 1rem;">${escapeHtml(dest.description)}</p>
            <div class="trip-meta-row" style="margin-bottom: 1.25rem;">
                <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Recommended: ${dest.recommended_duration_days} Days</div>
                <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost Index: ${'₹'.repeat(dest.cost_index || 2)}</div>
                <div class="trip-meta-item"><i class="fa-solid fa-fire"></i> Popularity: ${dest.popularity}/100</div>
            </div>
            <h4 style="margin-bottom: 0.75rem;">Top Curated Activities</h4>
            <div style="max-height: 200px; overflow-y: auto;">
                ${actsHtml}
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
            <button class="btn btn-primary" onclick="closeModal(); openAddToTripModal(${dest.id})">Add to Itinerary</button>
        </div>
    `);
}

// 14. Quick Add Destination to Existing Trip Modal
async function openAddToTripModal(cityId) {
    if (!state.user) {
        showToast('Please log in to add destinations to your trips.', 'info');
        openLoginModal();
        return;
    }

    const tRes = await apiRequest('/api/v1/trips');
    const trips = tRes.success ? (tRes.trips || []) : [];

    if (trips.length === 0) {
        showToast('Please create a trip first.', 'info');
        openCreateTripModal();
        return;
    }

    const optHtml = trips.map(t => `<option value="${t.id}">${escapeHtml(t.name)} (${formatDateRange(t.start_date, t.end_date)})</option>`).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">Add Destination to Trip</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddCityToSelectedTrip(${cityId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Select Target Trip</label>
                    <select id="target-trip-id" class="form-control">
                        ${optHtml}
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Stop &amp; Open Builder</button>
            </div>
        </form>
    `);
}

async function handleAddCityToSelectedTrip(cityId) {
    const tripId = document.getElementById('target-trip-id').value;
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops`, 'POST', { city_id: cityId });
    if (res.success) {
        closeModal();
        showToast('Destination added to itinerary!');
        navigateTo('itinerary', tripId);
    } else {
        showToast(res.error || 'Failed to add destination', 'error');
    }
}

// 15. User Profile Modal with Travel DNA Engine Visualizer
function openProfileModal() {
    if (!state.user) return;
    const dna = state.user.travel_dna || {
        adventure: 50, culture: 65, food: 70, relaxation: 45, sightseeing: 80, nature: 60, shopping: 55,
        persona_title: 'Balanced Explorer', insights: ['Balanced pacing with diverse cultural stops']
    };

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-user-gear" style="color: var(--primary);"></i> Traveler Profile &amp; Travel DNA</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleUpdateProfile();">
            <div class="modal-body">
                <!-- Travel DNA Visual Summary -->
                <div class="travel-dna-card" style="margin-bottom: 1.5rem; padding: 1.25rem;">
                    <div class="travel-dna-header" style="margin-bottom: 0.85rem;">
                        <div class="travel-dna-title" style="font-size: 1.15rem;">
                            <i class="fa-solid fa-dna" style="color: #F97316;"></i> Travel DNA
                        </div>
                        <span class="persona-badge-glow" style="font-size: 0.75rem;">
                            ${escapeHtml(dna.persona_title)}
                        </span>
                    </div>
                    <div class="dna-bars-grid" style="grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.5rem; margin: 0.5rem 0;">
                        <div class="dna-bar-item" style="padding: 0.5rem 0.75rem;">
                            <div class="dna-bar-header" style="font-size: 0.75rem;"><span>Adventure</span><span>${dna.adventure}%</span></div>
                            <div class="dna-bar-track"><div class="dna-bar-fill adventure" style="width: ${dna.adventure}%;"></div></div>
                        </div>
                        <div class="dna-bar-item" style="padding: 0.5rem 0.75rem;">
                            <div class="dna-bar-header" style="font-size: 0.75rem;"><span>Culture</span><span>${dna.culture}%</span></div>
                            <div class="dna-bar-track"><div class="dna-bar-fill culture" style="width: ${dna.culture}%;"></div></div>
                        </div>
                        <div class="dna-bar-item" style="padding: 0.5rem 0.75rem;">
                            <div class="dna-bar-header" style="font-size: 0.75rem;"><span>Food</span><span>${dna.food}%</span></div>
                            <div class="dna-bar-track"><div class="dna-bar-fill food" style="width: ${dna.food}%;"></div></div>
                        </div>
                        <div class="dna-bar-item" style="padding: 0.5rem 0.75rem;">
                            <div class="dna-bar-header" style="font-size: 0.75rem;"><span>Relaxation</span><span>${dna.relaxation}%</span></div>
                            <div class="dna-bar-track"><div class="dna-bar-fill relaxation" style="width: ${dna.relaxation}%;"></div></div>
                        </div>
                        <div class="dna-bar-item" style="padding: 0.5rem 0.75rem;">
                            <div class="dna-bar-header" style="font-size: 0.75rem;"><span>Sightseeing</span><span>${dna.sightseeing}%</span></div>
                            <div class="dna-bar-track"><div class="dna-bar-fill sightseeing" style="width: ${dna.sightseeing}%;"></div></div>
                        </div>
                    </div>
                </div>

                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">First Name</label>
                        <input type="text" id="prof-first-name" class="form-control" value="${escapeHtml(state.user.first_name || state.user.name.split(' ')[0] || '')}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Last Name</label>
                        <input type="text" id="prof-last-name" class="form-control" value="${escapeHtml(state.user.last_name || state.user.name.split(' ').slice(1).join(' ') || '')}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Email Address (Read-only)</label>
                        <input type="text" class="form-control" readonly value="${escapeHtml(state.user.email)}" disabled>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" id="prof-phone" class="form-control" value="${escapeHtml(state.user.phone || '')}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">City</label>
                        <input type="text" id="prof-city" class="form-control" value="${escapeHtml(state.user.city || '')}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Country</label>
                        <input type="text" id="prof-country" class="form-control" value="${escapeHtml(state.user.country || '')}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Preferred Currency</label>
                        <select id="prof-curr" class="form-control">
                            <option value="INR" ${state.user.preferred_currency === 'INR' ? 'selected' : ''}>₹ INR</option>
                            <option value="USD" ${state.user.preferred_currency === 'USD' ? 'selected' : ''}>$ USD</option>
                            <option value="EUR" ${state.user.preferred_currency === 'EUR' ? 'selected' : ''}>€ EUR</option>
                            <option value="GBP" ${state.user.preferred_currency === 'GBP' ? 'selected' : ''}>£ GBP</option>
                            <option value="AED" ${state.user.preferred_currency === 'AED' ? 'selected' : ''}>AED</option>
                            <option value="SGD" ${state.user.preferred_currency === 'SGD' ? 'selected' : ''}>S$ SGD</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="prof-style" class="form-control">
                            <option value="balanced" ${state.user.preferred_travel_style === 'balanced' ? 'selected' : ''}>Balanced Explorer</option>
                            <option value="budget" ${state.user.preferred_travel_style === 'budget' ? 'selected' : ''}>Budget Backpacker</option>
                            <option value="luxury" ${state.user.preferred_travel_style === 'luxury' ? 'selected' : ''}>Luxury &amp; Comfort</option>
                            <option value="adventure" ${state.user.preferred_travel_style === 'adventure' ? 'selected' : ''}>Active Adventure</option>
                            <option value="relaxed" ${state.user.preferred_travel_style === 'relaxed' ? 'selected' : ''}>Relaxed &amp; Slow Travel</option>
                            <option value="family" ${state.user.preferred_travel_style === 'family' ? 'selected' : ''}>Family Friendly</option>
                            <option value="solo" ${state.user.preferred_travel_style === 'solo' ? 'selected' : ''}>Solo Wanderer</option>
                            <option value="business" ${state.user.preferred_travel_style === 'business' ? 'selected' : ''}>Business</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Profile Avatar URL</label>
                    <input type="url" id="prof-avatar" class="form-control" value="${escapeHtml(state.user.avatar_url || '')}">
                </div>
                <div class="form-group">
                    <label class="form-label">Bio / Travel Manifesto</label>
                    <textarea id="prof-bio" class="form-control" rows="2">${escapeHtml(state.user.bio || state.user.additional_info || '')}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Close</button>
                <button type="submit" class="btn btn-primary btn-glow">Save Preferences</button>
            </div>
        </form>
    `);
}

async function handleUpdateProfile() {
    const firstName = document.getElementById('prof-first-name').value.trim();
    const lastName = document.getElementById('prof-last-name').value.trim();
    const fullName = `${firstName} ${lastName}`.trim() || state.user.name;
    const phone = document.getElementById('prof-phone').value.trim();
    const city = document.getElementById('prof-city').value.trim();
    const country = document.getElementById('prof-country').value.trim();
    const curr = document.getElementById('prof-curr').value;
    const style = document.getElementById('prof-style').value;
    const avatar = document.getElementById('prof-avatar').value.trim();
    const bio = document.getElementById('prof-bio').value.trim();

    const res = await apiRequest('/api/v1/auth/profile', 'PUT', {
        name: fullName,
        first_name: firstName,
        last_name: lastName,
        phone: phone,
        city: city,
        country: country,
        preferred_currency: curr,
        preferred_travel_style: style,
        avatar_url: avatar,
        bio: bio,
        additional_info: bio
    });

    if (res.success && res.user) {
        state.user = res.user;
        closeModal();
        renderAuthNav();
        showToast('Profile preferences & Travel DNA updated!');
    } else {
        showToast(res.error || 'Failed to update profile', 'error');
    }
}

// ================= Community Post Modals & Handlers =================
async function toggleCommunityLike(postId) {
    if (!state.user) {
        showToast('Please sign in to like community posts', 'info');
        openLoginModal();
        return;
    }

    const res = await apiRequest(`/api/v1/community/posts/${postId}/interact`, 'POST', { type: 'like' });
    if (res.success) {
        const countEl = document.getElementById(`post-likes-${postId}`);
        if (countEl) countEl.innerText = res.likes_count;
        const btn = countEl ? countEl.closest('.reaction-btn') : null;
        if (btn) {
            btn.classList.toggle('liked', res.active);
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = res.active ? 'fa-solid fa-heart' : 'fa-regular fa-heart';
            }
        }
        showToast(res.active ? 'Post liked!' : 'Like removed.');
    }
}

async function toggleCommunitySave(postId) {
    if (!state.user) {
        showToast('Please sign in to bookmark community posts', 'info');
        openLoginModal();
        return;
    }

    const res = await apiRequest(`/api/v1/community/posts/${postId}/interact`, 'POST', { type: 'save' });
    if (res.success) {
        const countEl = document.getElementById(`post-saves-${postId}`);
        if (countEl) countEl.innerText = res.saves_count;
        const btn = countEl ? countEl.closest('.reaction-btn') : null;
        if (btn) {
            btn.classList.toggle('saved', res.active);
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = res.active ? 'fa-solid fa-bookmark' : 'fa-regular fa-bookmark';
            }
        }
        showToast(res.active ? 'Story saved to your collection!' : 'Removed from saved.');
    }
}

async function openCommunityPostDetailModal(postId) {
    const res = await apiRequest(`/api/v1/community/posts/${postId}`);
    if (!res.success || !res.post) return;
    const p = res.post;
    const highlights = p.highlights || [];

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">${escapeHtml(p.title)}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div style="height: 220px; border-radius: var(--radius-md); overflow: hidden; margin-bottom: 1rem;">
                <img src="${p.cover_image || 'https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80'}" style="width: 100%; height: 100%; object-fit: cover;">
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <img src="${p.author_avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80'}" class="community-author-avatar">
                    <div>
                        <div style="font-weight: 700;">${escapeHtml(p.author_name)}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted);"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(p.city_name || 'India')}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <span class="badge-chip accent" style="text-transform: capitalize;">${escapeHtml(p.travel_style || 'Adventure')}</span>
                    <span class="badge-chip" style="background: #FEF3C7; color: #92400E;"><i class="fa-solid fa-star"></i> ${p.rating || 5.0}/5.0</span>
                    ${p.estimated_cost ? `<span class="badge-chip success">${formatCurrency(p.estimated_cost, 'INR')}</span>` : ''}
                </div>
            </div>

            <div style="font-size: 0.95rem; line-height: 1.6; color: var(--text-main); margin-bottom: 1.5rem; white-space: pre-line;">
                ${escapeHtml(p.content)}
            </div>

            ${highlights.length > 0 ? `
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1.25rem;">
                    <h4 style="font-size: 0.95rem; color: var(--primary); margin-bottom: 0.75rem;">
                        <i class="fa-solid fa-list-check"></i> Featured Activity Highlights (${highlights.length})
                    </h4>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        ${highlights.map(h => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-sm); font-size: 0.85rem;">
                                <div>
                                    <strong>${escapeHtml(h.name)}</strong>
                                    <span class="category-tag ${h.category || 'sightseeing'}" style="margin-left: 0.5rem;">${escapeHtml(h.category || 'sightseeing')}</span>
                                </div>
                                <span style="font-weight: 700; color: var(--primary);">${formatCurrency(h.estimated_cost, 'INR')}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
            <button class="btn btn-primary btn-glow" onclick="closeModal(); open1ClickImportModal(${p.id})">
                <i class="fa-solid fa-download"></i> 1-Click Import to Itinerary
            </button>
        </div>
    `);
}

// 1-Click Import to Itinerary Modal
let currentImportPost = null;
async function open1ClickImportModal(postId) {
    if (!state.user) {
        showToast('Please log in to import community itineraries into your account.', 'info');
        openLoginModal();
        return;
    }

    const [pRes, tRes] = await Promise.all([
        apiRequest(`/api/v1/community/posts/${postId}`),
        apiRequest('/api/v1/trips')
    ]);

    if (!pRes.success || !pRes.post) {
        showToast('Post details not found', 'error');
        return;
    }

    const post = pRes.post;
    currentImportPost = post;
    const trips = (tRes.success && tRes.trips) ? tRes.trips : [];

    if (trips.length === 0) {
        showToast('Please create a trip first to import activities.', 'info');
        openCreateTripModal();
        return;
    }

    const tripOptions = trips.map(t => `<option value="${t.id}">${escapeHtml(t.name)} (${t.duration_days} Days)</option>`).join('');
    const highlights = post.highlights || [];

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-file-import" style="color: var(--primary);"></i> 1-Click Import from "${escapeHtml(post.title)}"</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); submitCommunityImport(${post.id});">
            <div class="modal-body">
                <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 1.25rem;">
                    Select your destination trip, itinerary day, and check the experiences you'd like to import with estimated expenses.
                </p>

                <div class="form-group">
                    <label class="form-label">Destination Trip *</label>
                    <select id="import-trip-select" class="form-control" onchange="updateImportStopsDropdown(this.value)">
                        ${tripOptions}
                    </select>
                </div>

                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Destination Stop / City</label>
                        <select id="import-stop-select" class="form-control">
                            <option value="">(Auto-assign stop)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Target Day Number *</label>
                        <input type="number" id="import-day-number" class="form-control" required min="1" max="30" value="1">
                    </div>
                </div>

                <h4 style="font-size: 0.95rem; margin: 1.25rem 0 0.5rem; color: var(--text-main);">
                    Select Activities to Import (${highlights.length})
                </h4>
                <div style="max-height: 220px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.5rem; display: flex; flex-direction: column; gap: 0.4rem;">
                    ${highlights.map((h, idx) => `
                        <label style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.75rem; background: #F8FAFC; border-radius: var(--radius-sm); cursor: pointer;">
                            <div style="display: flex; align-items: center; gap: 0.6rem;">
                                <input type="checkbox" class="import-act-checkbox" data-index="${idx}" checked style="width: 17px; height: 17px;">
                                <div>
                                    <strong style="font-size: 0.88rem;">${escapeHtml(h.name)}</strong>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(h.category || 'sightseeing')} · ${h.duration_hours || 2}h</div>
                                </div>
                            </div>
                            <span style="font-weight: 700; color: var(--primary); font-size: 0.85rem;">${formatCurrency(h.estimated_cost, 'INR')}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary btn-glow">
                    <i class="fa-solid fa-download"></i> Confirm &amp; Import to Trip
                </button>
            </div>
        </form>
    `);

    // populate initial stop dropdown
    updateImportStopsDropdown(trips[0].id);
}

async function updateImportStopsDropdown(tripId) {
    const stopSelect = document.getElementById('import-stop-select');
    if (!stopSelect) return;
    const res = await apiRequest(`/api/v1/trips/${tripId}`);
    if (res.success && res.trip) {
        const stops = res.trip.stops || [];
        stopSelect.innerHTML = stops.length > 0 ?
            stops.map(s => `<option value="${s.id}">${escapeHtml(s.city_name)}</option>`).join('') :
            `<option value="">(No stops defined yet)</option>`;
    }
}

async function submitCommunityImport(postId) {
    if (!currentImportPost) return;
    const tripId = parseInt(document.getElementById('import-trip-select').value);
    const stopId = document.getElementById('import-stop-select').value ? parseInt(document.getElementById('import-stop-select').value) : null;
    const targetDay = parseInt(document.getElementById('import-day-number').value) || 1;

    const checkboxes = document.querySelectorAll('.import-act-checkbox:checked');
    const highlights = currentImportPost.highlights || [];
    const selectedActs = Array.from(checkboxes).map(cb => highlights[parseInt(cb.dataset.index)]).filter(Boolean);

    if (selectedActs.length === 0) {
        showToast('Please select at least one activity to import', 'error');
        return;
    }

    const res = await apiRequest(`/api/v1/community/posts/${postId}/import`, 'POST', {
        trip_id: tripId,
        stop_id: stopId,
        day_number: targetDay,
        activities: selectedActs
    });

    if (res.success) {
        closeModal();
        showToast(`Successfully imported ${res.imported_count} activities (${formatCurrency(res.imported_cost, 'INR')}) into your itinerary!`, 'success');
        navigateTo('itinerary', tripId);
    } else {
        showToast(res.error || 'Failed to import activities', 'error');
    }
}

// Create Community Post Modal
function openCreateCommunityPostModal() {
    if (!state.user) {
        showToast('Please log in to publish your travel stories', 'info');
        openLoginModal();
        return;
    }

    const destinations = state.destinations || [];
    const cityOptions = destinations.map(d => `<option value="${d.id}">${escapeHtml(d.name)}, ${escapeHtml(d.country)}</option>`).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-pen-nib" style="color: var(--primary);"></i> Share Your Travel Story</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); submitCreateCommunityPost();">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Story / Experience Title *</label>
                    <input type="text" id="post-title" class="form-control" required placeholder="e.g. 48 Hours of Royal Heritage in Jaipur">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Destination City</label>
                        <select id="post-city" class="form-control">
                            ${cityOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="post-style" class="form-control">
                            <option value="adventure">Adventure</option>
                            <option value="culture" selected>Culture</option>
                            <option value="food">Food &amp; Dining</option>
                            <option value="luxury">Luxury</option>
                            <option value="budget">Budget</option>
                            <option value="relaxed">Relaxed</option>
                        </select>
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Rating (1 to 5 Stars)</label>
                        <input type="number" step="0.1" id="post-rating" class="form-control" min="1" max="5" value="4.8">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Estimated Total Spend (INR)</label>
                        <input type="number" id="post-cost" class="form-control" min="0" value="8500">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Cover Photo URL</label>
                    <input type="url" id="post-cover" class="form-control" value="https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80">
                </div>
                <div class="form-group">
                    <label class="form-label">Your Travel Story &amp; Tips *</label>
                    <textarea id="post-content" class="form-control" rows="4" required placeholder="Share what made this journey special, key timing tips, where to eat..."></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Tags (comma-separated)</label>
                    <input type="text" id="post-tags" class="form-control" value="Rajasthan, Heritage, Photography, Palaces">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary btn-glow">Publish to Community</button>
            </div>
        </form>
    `);
}

async function submitCreateCommunityPost() {
    const title = document.getElementById('post-title').value.trim();
    const cityId = document.getElementById('post-city').value;
    const style = document.getElementById('post-style').value;
    const rating = parseFloat(document.getElementById('post-rating').value) || 5.0;
    const cost = parseFloat(document.getElementById('post-cost').value) || 0;
    const cover = document.getElementById('post-cover').value.trim();
    const content = document.getElementById('post-content').value.trim();
    const tags = document.getElementById('post-tags').value.split(',').map(t => t.trim()).filter(Boolean);

    const highlights = [
        { name: `${title} Highlight Tour`, category: style, estimated_cost: cost * 0.4, duration_hours: 3.0, time: "10:00" },
        { name: `Traditional Local Tasting in ${style}`, category: 'food', estimated_cost: cost * 0.2, duration_hours: 1.5, time: "13:30" }
    ];

    const res = await apiRequest('/api/v1/community/posts', 'POST', {
        title,
        city_id: cityId ? parseInt(cityId) : null,
        travel_style: style,
        rating,
        estimated_cost: cost,
        cover_image: cover,
        content,
        tags,
        highlights
    });

    if (res.success) {
        closeModal();
        showToast('Your travel story has been published to the community!', 'success');
        renderCommunityHub();
    } else {
        showToast(res.error || 'Failed to publish story', 'error');
    }
}

// ================= Universal Global Search (Ctrl+K) =================
function openGlobalSearchModal() {
    openModal(`
        <div class="search-modal-box">
            <div class="search-input-header">
                <i class="fa-solid fa-magnifying-glass" style="color: var(--primary); font-size: 1.25rem;"></i>
                <input type="text" id="global-search-query" placeholder="Search destinations, activities, stays, trips, and community..." autofocus onkeyup="handleGlobalSearchInput(this.value)">
                <kbd class="search-kbd">ESC</kbd>
            </div>
            <div class="search-results-container" id="global-search-results">
                <div style="padding: 2rem; text-align: center; color: var(--text-muted);">
                    <i class="fa-solid fa-compass" style="font-size: 2rem; margin-bottom: 0.5rem; color: var(--primary);"></i>
                    <div>Type to search instantly across all GlobeTrotter travel resources.</div>
                </div>
            </div>
        </div>
    `);

    setTimeout(() => {
        const input = document.getElementById('global-search-query');
        if (input) input.focus();
    }, 50);
}

let searchDebounceTimer = null;
async function handleGlobalSearchInput(query) {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(async () => {
        const container = document.getElementById('global-search-results');
        if (!container) return;

        if (!query.trim()) {
            container.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: var(--text-muted);">
                    <i class="fa-solid fa-compass" style="font-size: 2rem; margin-bottom: 0.5rem; color: var(--primary);"></i>
                    <div>Type to search instantly across all GlobeTrotter travel resources.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Searching...</div>`;

        const res = await apiRequest(`/api/v1/search?q=${encodeURIComponent(query.trim())}`);
        if (!res.success || !res.results) {
            container.innerHTML = `<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No matching results.</div>`;
            return;
        }

        const r = res.results;
        let html = '';

        // 1. Destinations
        if (r.destinations && r.destinations.length > 0) {
            html += `
                <div class="search-category-group">
                    <div class="search-category-title"><i class="fa-solid fa-map-location-dot"></i> Destinations (${r.destinations.length})</div>
                    ${r.destinations.map(d => `
                        <div class="search-result-item" onclick="closeModal(); openDestinationDetailModal(${d.id})">
                            <div class="search-result-icon" style="background: #EEF2FF; color: #4F46E5;"><i class="fa-solid fa-city"></i></div>
                            <div>
                                <strong style="font-size: 0.92rem;">${escapeHtml(d.name)}, ${escapeHtml(d.country)}</strong>
                                <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(d.description.substring(0, 70))}...</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 2. Activities
        if (r.activities && r.activities.length > 0) {
            html += `
                <div class="search-category-group">
                    <div class="search-category-title"><i class="fa-solid fa-ticket"></i> Curated Activities (${r.activities.length})</div>
                    ${r.activities.map(a => `
                        <div class="search-result-item" onclick="closeModal(); openScheduleCatalogActModal(${a.id})">
                            <div class="search-result-icon" style="background: #ECFDF5; color: #059669;"><i class="fa-solid fa-ticket"></i></div>
                            <div>
                                <strong style="font-size: 0.92rem;">${escapeHtml(a.name)}</strong>
                                <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(a.city_name || '')} · ${formatCurrency(a.estimated_cost, 'INR')}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 3. Hotels
        if (r.hotels && r.hotels.length > 0) {
            html += `
                <div class="search-category-group">
                    <div class="search-category-title"><i class="fa-solid fa-hotel"></i> Recommended Hotels (${r.hotels.length})</div>
                    ${r.hotels.map(h => `
                        <div class="search-result-item" onclick="closeModal();">
                            <div class="search-result-icon" style="background: #FAF5FF; color: #7C3AED;"><i class="fa-solid fa-bed"></i></div>
                            <div>
                                <strong style="font-size: 0.92rem;">${escapeHtml(h.name)}</strong>
                                <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(h.city_name || '')} · ⭐ ${h.rating} · ${formatCurrency(h.price_per_night, 'INR')}/nt</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 4. Community Stories
        if (r.community && r.community.length > 0) {
            html += `
                <div class="search-category-group">
                    <div class="search-category-title"><i class="fa-solid fa-users"></i> Community Stories (${r.community.length})</div>
                    ${r.community.map(p => `
                        <div class="search-result-item" onclick="closeModal(); openCommunityPostDetailModal(${p.id})">
                            <div class="search-result-icon" style="background: #FFF7ED; color: #C2410C;"><i class="fa-solid fa-book-open"></i></div>
                            <div>
                                <strong style="font-size: 0.92rem;">${escapeHtml(p.title)}</strong>
                                <div style="font-size: 0.78rem; color: var(--text-muted);">By ${escapeHtml(p.author_name || 'Traveler')} · ⭐ ${p.rating}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        if (!html) {
            html = `<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No results found for "${escapeHtml(query)}"</div>`;
        }

        container.innerHTML = html;
    }, 200);
}

// Global Keyboard Shortcut: Ctrl+K or Cmd+K
window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openGlobalSearchModal();
    }
});

// ================= Hotel Recommendations & Accommodations Management =================
let hotelSearchContext = {
    stopId: null,
    cityId: null,
    cityName: '',
    checkIn: '',
    checkOut: '',
    guests: 2,
    rooms: 1,
    category: 'all',
    minRating: 0,
    minPrice: 0,
    maxPrice: 0,
    amenities: '',
    sortBy: 'recommended',
    allHotels: [],
    compareIds: []
};

async function openHotelSearchModal(stopId, cityId, cityName, arrivalDate, departureDate) {
    hotelSearchContext.stopId = stopId;
    hotelSearchContext.cityId = cityId;
    hotelSearchContext.cityName = cityName;
    hotelSearchContext.checkIn = arrivalDate || (state.currentTrip ? state.currentTrip.start_date : '') || new Date().toISOString().split('T')[0];
    hotelSearchContext.checkOut = departureDate || (state.currentTrip ? state.currentTrip.end_date : '') || new Date().toISOString().split('T')[0];
    hotelSearchContext.guests = state.currentTrip ? (state.currentTrip.travelers_count || 2) : 2;
    hotelSearchContext.rooms = Math.max(1, Math.ceil(hotelSearchContext.guests / 2));
    hotelSearchContext.category = 'all';
    hotelSearchContext.minRating = 0;
    hotelSearchContext.minPrice = 0;
    hotelSearchContext.maxPrice = 0;
    hotelSearchContext.amenities = '';
    hotelSearchContext.sortBy = 'recommended';
    hotelSearchContext.compareIds = [];

    openModal(`
        <div class="modal-header">
            <div>
                <h2 class="modal-title"><i class="fa-solid fa-hotel" style="color: var(--primary);"></i> Hotel Recommendations in ${escapeHtml(cityName)}</h2>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">
                    Curated stays scored against your itinerary dates, group size, and remaining budget.
                </div>
            </div>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body" style="padding-top: 0.5rem;">
            <!-- Top Search Context Bar -->
            <div style="background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: var(--radius-md); padding: 0.85rem 1rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; font-size: 0.88rem;">
                    <div>
                        <span style="font-weight: 600; color: #6B21A8;">Check-in:</span>
                        <input type="date" id="hotel-search-checkin" class="form-control" style="display: inline-block; width: auto; padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${hotelSearchContext.checkIn}" onchange="updateHotelSearchDates()">
                    </div>
                    <div>
                        <span style="font-weight: 600; color: #6B21A8;">Check-out:</span>
                        <input type="date" id="hotel-search-checkout" class="form-control" style="display: inline-block; width: auto; padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${hotelSearchContext.checkOut}" onchange="updateHotelSearchDates()">
                    </div>
                    <div>
                        <span style="font-weight: 600; color: #6B21A8;">Guests:</span>
                        <input type="number" id="hotel-search-guests" min="1" max="20" class="form-control" style="display: inline-block; width: 65px; padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${hotelSearchContext.guests}" onchange="updateHotelSearchDates()">
                    </div>
                    <div>
                        <span style="font-weight: 600; color: #6B21A8;">Rooms:</span>
                        <input type="number" id="hotel-search-rooms" min="1" max="10" class="form-control" style="display: inline-block; width: 60px; padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${hotelSearchContext.rooms}" onchange="updateHotelSearchDates()">
                    </div>
                </div>
                <div id="compare-floating-trigger" style="display: none;">
                    <button class="btn btn-accent btn-sm" onclick="openHotelComparisonModal()">
                        <i class="fa-solid fa-code-compare"></i> Compare (<span id="compare-count">0</span>) Hotels
                    </button>
                </div>
            </div>

            <!-- Main Layout: Filter Sidebar + Hotel Cards List -->
            <div class="hotel-search-modal-layout">
                <!-- Sidebar Filters -->
                <div class="hotel-filter-sidebar">
                    <div>
                        <div class="filter-group-title">Category Tier</div>
                        <div class="filter-chips-grid">
                            <button type="button" class="filter-chip active" onclick="setHotelCategoryFilter('all', this)">All</button>
                            <button type="button" class="filter-chip" onclick="setHotelCategoryFilter('budget', this)">Budget</button>
                            <button type="button" class="filter-chip" onclick="setHotelCategoryFilter('economy', this)">Economy</button>
                            <button type="button" class="filter-chip" onclick="setHotelCategoryFilter('mid_range', this)">Mid-Range</button>
                            <button type="button" class="filter-chip" onclick="setHotelCategoryFilter('premium', this)">Premium</button>
                            <button type="button" class="filter-chip" onclick="setHotelCategoryFilter('luxury', this)">Luxury</button>
                        </div>
                    </div>

                    <div>
                        <div class="filter-group-title">Guest Rating</div>
                        <div class="filter-chips-grid">
                            <button type="button" class="filter-chip active" onclick="setHotelRatingFilter(0, this)">Any</button>
                            <button type="button" class="filter-chip" onclick="setHotelRatingFilter(4.0, this)">⭐ 4.0+</button>
                            <button type="button" class="filter-chip" onclick="setHotelRatingFilter(4.5, this)">⭐ 4.5+</button>
                            <button type="button" class="filter-chip" onclick="setHotelRatingFilter(4.8, this)">⭐ 4.8+</button>
                        </div>
                    </div>

                    <div>
                        <div class="filter-group-title">Price Range / Night</div>
                        <div class="filter-chips-grid">
                            <button type="button" class="filter-chip active" onclick="setHotelPriceFilter(0, 0, this)">All</button>
                            <button type="button" class="filter-chip" onclick="setHotelPriceFilter(0, 3000, this)">&lt; ₹3,000</button>
                            <button type="button" class="filter-chip" onclick="setHotelPriceFilter(3000, 8000, this)">₹3k - ₹8k</button>
                            <button type="button" class="filter-chip" onclick="setHotelPriceFilter(8000, 20000, this)">₹8k - ₹20k</button>
                            <button type="button" class="filter-chip" onclick="setHotelPriceFilter(20000, 0, this)">₹20,000+</button>
                        </div>
                    </div>

                    <div>
                        <div class="filter-group-title">Must-Have Amenities</div>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="wifi" onchange="toggleHotelAmenityFilter('wifi', this.checked)"> High-Speed Wi-Fi
                        </label>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="breakfast" onchange="toggleHotelAmenityFilter('breakfast', this.checked)"> Breakfast Included
                        </label>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="pool" onchange="toggleHotelAmenityFilter('pool', this.checked)"> Swimming Pool
                        </label>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="spa" onchange="toggleHotelAmenityFilter('spa', this.checked)"> Luxury Spa / Wellness
                        </label>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="restaurant" onchange="toggleHotelAmenityFilter('restaurant', this.checked)"> Fine Restaurant / Bar
                        </label>
                        <label class="filter-checkbox-label">
                            <input type="checkbox" value="parking" onchange="toggleHotelAmenityFilter('parking', this.checked)"> Free Parking
                        </label>
                    </div>
                </div>

                <!-- Right Side Results Container -->
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
                        <span id="hotel-results-count" style="font-size: 0.9rem; font-weight: 700; color: var(--text-muted);">
                            Loading recommendations...
                        </span>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted);">Sort By:</label>
                            <select id="hotel-sort-select" class="form-control" style="width: auto; padding: 0.3rem 0.6rem; font-size: 0.85rem;" onchange="setHotelSort(this.value)">
                                <option value="recommended">🏆 Recommended Score</option>
                                <option value="price_asc">Price: Low to High</option>
                                <option value="price_desc">Price: High to Low</option>
                                <option value="rating">Guest Rating</option>
                                <option value="value">Best Value for Money</option>
                                <option value="location">Best Location Score</option>
                            </select>
                        </div>
                    </div>
                    <div id="hotel-cards-container" class="hotel-cards-list">
                        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                            <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary); margin-bottom: 0.75rem;"></i>
                            <div>Finding best hotel matches for your trip...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    await fetchAndRenderHotelRecommendations();
}

async function updateHotelSearchDates() {
    const checkIn = document.getElementById('hotel-search-checkin').value;
    const checkOut = document.getElementById('hotel-search-checkout').value;
    const guests = parseInt(document.getElementById('hotel-search-guests').value) || 2;
    const rooms = parseInt(document.getElementById('hotel-search-rooms').value) || 1;

    hotelSearchContext.checkIn = checkIn;
    hotelSearchContext.checkOut = checkOut;
    hotelSearchContext.guests = guests;
    hotelSearchContext.rooms = rooms;

    await fetchAndRenderHotelRecommendations();
}

function setHotelCategoryFilter(cat, elem) {
    hotelSearchContext.category = cat;
    elem.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    elem.classList.add('active');
    fetchAndRenderHotelRecommendations();
}

function setHotelRatingFilter(minR, elem) {
    hotelSearchContext.minRating = minR;
    elem.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    elem.classList.add('active');
    fetchAndRenderHotelRecommendations();
}

function setHotelPriceFilter(minP, maxP, elem) {
    hotelSearchContext.minPrice = minP;
    hotelSearchContext.maxPrice = maxP;
    elem.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    elem.classList.add('active');
    fetchAndRenderHotelRecommendations();
}

function toggleHotelAmenityFilter(amenity, isChecked) {
    let list = hotelSearchContext.amenities ? hotelSearchContext.amenities.split(',').map(a => a.trim()) : [];
    if (isChecked) {
        if (!list.includes(amenity)) list.push(amenity);
    } else {
        list = list.filter(a => a !== amenity);
    }
    hotelSearchContext.amenities = list.join(',');
    fetchAndRenderHotelRecommendations();
}

function setHotelSort(sortBy) {
    hotelSearchContext.sortBy = sortBy;
    fetchAndRenderHotelRecommendations();
}

async function fetchAndRenderHotelRecommendations() {
    const container = document.getElementById('hotel-cards-container');
    const countLabel = document.getElementById('hotel-results-count');
    if (!container) return;

    const tripId = state.currentTrip ? state.currentTrip.id : '';
    const queryParams = new URLSearchParams({
        city_id: hotelSearchContext.cityId || '',
        city: hotelSearchContext.cityName || '',
        trip_id: tripId,
        check_in: hotelSearchContext.checkIn,
        check_out: hotelSearchContext.checkOut,
        guests: hotelSearchContext.guests,
        rooms: hotelSearchContext.rooms,
        category: hotelSearchContext.category,
        min_rating: hotelSearchContext.minRating,
        min_price: hotelSearchContext.minPrice,
        max_price: hotelSearchContext.maxPrice,
        amenities: hotelSearchContext.amenities,
        sort_by: hotelSearchContext.sortBy
    });

    const res = await apiRequest(`/api/v1/hotels/recommendations?${queryParams.toString()}`);
    if (!res.success) {
        container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--danger);">${escapeHtml(res.error || 'Failed to load hotels')}</div>`;
        return;
    }

    const hotels = res.hotels || [];
    hotelSearchContext.allHotels = hotels;

    if (countLabel) {
        countLabel.textContent = `${hotels.length} Recommended Hotel${hotels.length !== 1 ? 's' : ''} in ${hotelSearchContext.cityName}`;
    }

    if (hotels.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; background: #F8FAFC; border: 1px dashed var(--border-color); border-radius: var(--radius-lg);">
                <i class="fa-solid fa-hotel" style="font-size: 2.5rem; color: var(--text-muted); margin-bottom: 0.75rem;"></i>
                <h4 style="font-size: 1.1rem; margin-bottom: 0.35rem;">No Hotels Matching Your Active Filters</h4>
                <p style="font-size: 0.85rem; color: var(--text-muted);">Try adjusting your category, price range, or amenities filters.</p>
            </div>
        `;
        return;
    }

    const curr = state.currentTrip ? state.currentTrip.currency : 'INR';

    container.innerHTML = hotels.map(hotel => {
        const isCompared = hotelSearchContext.compareIds.includes(hotel.id);
        const nights = res.search_criteria ? res.search_criteria.nights : 1;
        const totalStay = Number(hotel.total_stay_cost) || (Number(hotel.price_per_night) * nights * hotelSearchContext.rooms);
        const scoreClass = hotel.recommendation_score >= 90 ? 'high' : (hotel.recommendation_score >= 75 ? 'med' : 'fair');
        const primaryBadge = hotel.primary_badge || { label: "✨ Recommended", class: "badge-top-rec" };

        const amenitiesList = (hotel.amenities || '').split(',').map(a => a.trim()).filter(Boolean);

        return `
            <div class="hotel-card-item">
                <div class="hotel-card-photo-wrap">
                    <img src="${hotel.image || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=400&q=80'}" alt="${escapeHtml(hotel.name)}">
                    <span class="hotel-category-badge">${escapeHtml((hotel.hotel_category || 'hotel').replace('_', '-'))}</span>
                </div>
                <div class="hotel-card-main">
                    <div class="hotel-card-header">
                        <div>
                            <span class="hotel-badge-tag ${primaryBadge.class}">${escapeHtml(primaryBadge.label)}</span>
                            <div class="hotel-card-name">${escapeHtml(hotel.name)}</div>
                        </div>
                        <div class="match-score-pill ${scoreClass}" title="Recommendation Score">
                            <i class="fa-solid fa-gauge-high"></i> ${hotel.recommendation_score}/100
                        </div>
                    </div>
                    <div class="hotel-card-location">
                        <i class="fa-solid fa-location-dot" style="color: var(--primary);"></i>
                        ${escapeHtml(hotel.address || hotel.city_name)} &bull; 
                        <span><i class="fa-solid fa-star" style="color: #F59E0B;"></i> ${hotel.rating}/5.0 (${hotel.review_count || 120} reviews)</span>
                    </div>

                    ${hotel.fits_budget ? `
                        <div class="budget-fit-alert fits">
                            <i class="fa-solid fa-circle-check"></i> Fits within your remaining trip budget
                        </div>
                    ` : `
                        <div class="budget-fit-alert exceeds">
                            <i class="fa-solid fa-triangle-exclamation"></i> May exceed remaining budget (Consider economy room or style adjustments)
                        </div>
                    `}

                    <!-- Why this hotel data-driven box -->
                    <div class="why-this-hotel-box">
                        <h5><i class="fa-solid fa-wand-magic-sparkles"></i> Why this hotel matches your plan:</h5>
                        <ul class="why-this-hotel-list">
                            ${(hotel.why_points || []).slice(0, 3).map(p => `<li><i class="fa-solid fa-check"></i> <span>${escapeHtml(p)}</span></li>`).join('')}
                        </ul>
                    </div>

                    <div class="hotel-amenities-tags">
                        ${amenitiesList.slice(0, 5).map(a => `<span class="amenity-pill"><i class="fa-solid fa-check" style="font-size:0.65rem;"></i> ${escapeHtml(a.replace('_', ' '))}</span>`).join('')}
                        ${amenitiesList.length > 5 ? `<span class="amenity-pill">+${amenitiesList.length - 5} more</span>` : ''}
                    </div>
                </div>

                <div class="hotel-card-pricing">
                    <div>
                        <div class="hotel-price-per-night">${formatCurrency(hotel.price_per_night, curr)}</div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.35rem;">per night</div>
                        <div class="hotel-stay-total">
                            <strong>${formatCurrency(totalStay, curr)}</strong> for ${nights} night${nights > 1 ? 's' : ''}, ${hotelSearchContext.rooms} room${hotelSearchContext.rooms > 1 ? 's' : ''}
                        </div>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="handleConfirmAddHotel(${hotel.id}, ${hotelSearchContext.stopId}, '${hotelSearchContext.checkIn}', '${hotelSearchContext.checkOut}', ${hotelSearchContext.guests}, ${hotelSearchContext.rooms})">
                            <i class="fa-solid fa-plus"></i> Select &amp; Add Hotel
                        </button>
                        <div style="display: flex; gap: 0.35rem;">
                            <button class="btn btn-outline btn-sm" style="flex: 1;" onclick="openHotelDetailModal(${hotel.id}, ${hotelSearchContext.stopId}, '${hotelSearchContext.checkIn}', '${hotelSearchContext.checkOut}', ${hotelSearchContext.guests}, ${hotelSearchContext.rooms})">
                                Details
                            </button>
                            <button class="btn ${isCompared ? 'btn-accent' : 'btn-subtle'} btn-sm" onclick="toggleHotelCompare(${hotel.id})" title="Compare side by side">
                                <i class="fa-solid fa-code-compare"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function toggleHotelCompare(hotelId) {
    const index = hotelSearchContext.compareIds.indexOf(hotelId);
    if (index >= 0) {
        hotelSearchContext.compareIds.splice(index, 1);
    } else {
        if (hotelSearchContext.compareIds.length >= 3) {
            showToast('You can compare up to 3 hotels at once.', 'info');
            return;
        }
        hotelSearchContext.compareIds.push(hotelId);
    }

    const trig = document.getElementById('compare-floating-trigger');
    const countSpan = document.getElementById('compare-count');
    if (trig && countSpan) {
        countSpan.textContent = hotelSearchContext.compareIds.length;
        trig.style.display = hotelSearchContext.compareIds.length >= 2 ? 'block' : 'none';
    }

    fetchAndRenderHotelRecommendations();
}

async function openHotelComparisonModal() {
    if (hotelSearchContext.compareIds.length < 2) {
        showToast('Please select at least 2 hotels to compare.', 'info');
        return;
    }

    const tripId = state.currentTrip ? state.currentTrip.id : '';
    const res = await apiRequest(`/api/v1/hotels/compare?ids=${hotelSearchContext.compareIds.join(',')}&trip_id=${tripId}&nights=1&rooms=${hotelSearchContext.rooms}`);
    if (!res.success || !res.comparison) {
        showToast(res.error || 'Failed to load comparison', 'error');
        return;
    }

    const hotels = res.comparison;
    const curr = state.currentTrip ? state.currentTrip.currency : 'INR';

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-code-compare" style="color: var(--accent);"></i> Side-by-Side Hotel Comparison</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div class="comparison-table-wrap">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Feature</th>
                            ${hotels.map(h => `
                                <td style="text-align: center; min-width: 220px;">
                                    <img src="${h.image}" style="width: 100%; height: 110px; object-fit: cover; border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
                                    <div style="font-weight: 700; font-size: 1.05rem;">${escapeHtml(h.name)}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(h.city_name)}</div>
                                </td>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th>Recommendation Score</th>
                            ${hotels.map(h => `
                                <td style="text-align: center; font-weight: 800; font-size: 1.1rem; color: var(--primary);">
                                    ${h.recommendation_score}/100 <br>
                                    <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted);">${h.match_tier}</span>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <th>Price / Night</th>
                            ${hotels.map(h => `
                                <td style="text-align: center; font-weight: 700; font-size: 1.1rem;">
                                    ${formatCurrency(h.price_per_night, curr)}
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <th>Category &amp; Rating</th>
                            ${hotels.map(h => `
                                <td style="text-align: center;">
                                    <span class="hotel-category-badge" style="position:static; display:inline-block; margin-bottom: 0.25rem;">${escapeHtml((h.hotel_category || '').replace('_', '-'))}</span>
                                    <div>⭐ ${h.rating}/5.0 (${h.review_count || 100} reviews)</div>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <th>Quality Sub-Scores</th>
                            ${hotels.map(h => `
                                <td style="font-size: 0.82rem; line-height: 1.6;">
                                    <div>📍 Location: <strong>${h.location_score}/10</strong></div>
                                    <div>✨ Cleanliness: <strong>${h.cleanliness_score}/10</strong></div>
                                    <div>🛎️ Service: <strong>${h.service_score}/10</strong></div>
                                    <div>💎 Value: <strong>${h.value_score}/10</strong></div>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <th>Amenities</th>
                            ${hotels.map(h => `
                                <td>
                                    <div class="hotel-amenities-tags">
                                        ${(h.amenities || '').split(',').map(a => `<span class="amenity-pill">${escapeHtml(a.trim().replace('_', ' '))}</span>`).join('')}
                                    </div>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <th>Action</th>
                            ${hotels.map(h => `
                                <td style="text-align: center;">
                                    <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="closeModal(); handleConfirmAddHotel(${h.id}, ${hotelSearchContext.stopId}, '${hotelSearchContext.checkIn}', '${hotelSearchContext.checkOut}', ${hotelSearchContext.guests}, ${hotelSearchContext.rooms})">
                                        Choose This Hotel
                                    </button>
                                </td>
                            `).join('')}
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
        </div>
    `);
}

async function openHotelDetailModal(hotelId, stopId, checkIn, checkOut, guests, rooms) {
    const res = await apiRequest(`/api/v1/hotels/${hotelId}`);
    if (!res.success || !res.hotel) {
        showToast('Failed to load hotel profile', 'error');
        return;
    }

    const h = res.hotel;
    const curr = state.currentTrip ? state.currentTrip.currency : 'INR';
    const amenitiesList = (h.amenities || '').split(',').map(a => a.trim()).filter(Boolean);

    openModal(`
        <div class="modal-header">
            <div>
                <h2 class="modal-title">${escapeHtml(h.name)}</h2>
                <div style="font-size: 0.85rem; color: var(--text-muted);">
                    <i class="fa-solid fa-location-dot" style="color: var(--primary);"></i> ${escapeHtml(h.address || h.city_name)}, ${escapeHtml(h.country_name)}
                </div>
            </div>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <img src="${h.image}" style="width: 100%; height: 220px; object-fit: cover; border-radius: var(--radius-md); margin-bottom: 1rem;">
            <p style="color: var(--text-main); line-height: 1.6; margin-bottom: 1rem;">${escapeHtml(h.description)}</p>

            <div class="trip-meta-row" style="margin-bottom: 1.25rem;">
                <div class="trip-meta-item">⭐ ${h.rating}/5.0 (${h.review_count || 120} reviews)</div>
                <div class="trip-meta-item">🏷️ ${escapeHtml((h.hotel_category || 'hotel').replace('_', '-').toUpperCase())}</div>
                <div class="trip-meta-item">💰 ${formatCurrency(h.price_per_night, curr)} / night</div>
                <div class="trip-meta-item">👥 Up to ${h.max_guests || 2} guests/room</div>
            </div>

            <!-- Quality Rating Scores -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem; text-align: center; margin-bottom: 1.25rem;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Location</div>
                    <div style="font-weight: 800; font-size: 1.1rem; color: var(--primary);">${h.location_score}/10</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Cleanliness</div>
                    <div style="font-weight: 800; font-size: 1.1rem; color: var(--primary);">${h.cleanliness_score}/10</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Service</div>
                    <div style="font-weight: 800; font-size: 1.1rem; color: var(--primary);">${h.service_score}/10</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Value</div>
                    <div style="font-weight: 800; font-size: 1.1rem; color: var(--primary);">${h.value_score}/10</div>
                </div>
            </div>

            <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem;">Property Amenities</h4>
            <div class="hotel-amenities-tags" style="margin-bottom: 1.25rem;">
                ${amenitiesList.map(a => `<span class="amenity-pill"><i class="fa-solid fa-check"></i> ${escapeHtml(a.replace('_', ' '))}</span>`).join('')}
            </div>

            <!-- Booking Room Config -->
            <div style="background: #FAF8FF; border: 1.5px solid #E9D5FF; border-radius: var(--radius-md); padding: 1rem;">
                <h4 style="font-size: 0.95rem; color: #6B21A8; margin-bottom: 0.65rem;"><i class="fa-solid fa-calendar-check"></i> Reserve Accommodation</h4>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Check-in Date</label>
                        <input type="date" id="detail-checkin" class="form-control" value="${checkIn}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Check-out Date</label>
                        <input type="date" id="detail-checkout" class="form-control" value="${checkOut}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Rooms</label>
                        <input type="number" id="detail-rooms" min="1" max="10" class="form-control" value="${rooms || 1}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Guests</label>
                        <input type="number" id="detail-guests" min="1" max="20" class="form-control" value="${guests || 2}">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Special Requests / Room Type</label>
                    <input type="text" id="detail-roomtype" class="form-control" placeholder="e.g. Deluxe King Room with Balcony">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeModal()">Back</button>
            <button class="btn btn-primary" onclick="submitDetailedHotelBooking(${h.id}, ${stopId})">
                Confirm &amp; Add Hotel to Trip
            </button>
        </div>
    `);
}

async function submitDetailedHotelBooking(hotelId, stopId) {
    const checkIn = document.getElementById('detail-checkin').value;
    const checkOut = document.getElementById('detail-checkout').value;
    const rooms = parseInt(document.getElementById('detail-rooms').value) || 1;
    const guests = parseInt(document.getElementById('detail-guests').value) || 2;
    const roomType = document.getElementById('detail-roomtype').value.trim() || 'Standard Double Room';

    await handleConfirmAddHotel(hotelId, stopId, checkIn, checkOut, guests, rooms, roomType);
}

async function handleConfirmAddHotel(hotelId, stopId, checkIn, checkOut, guests, rooms, roomType = 'Standard Double Room', notes = '') {
    if (!state.currentTrip) {
        showToast('Please open a trip first', 'error');
        return;
    }

    const tripId = state.currentTrip.id;
    const res = await apiRequest(`/api/v1/trips/${tripId}/hotels`, 'POST', {
        hotel_id: hotelId,
        stop_id: stopId,
        check_in: checkIn,
        check_out: checkOut,
        number_of_guests: guests,
        number_of_rooms: rooms,
        room_type_selected: roomType,
        notes: notes
    });

    if (res.success) {
        closeModal();
        showToast(res.message || 'Hotel accommodation added to your itinerary & budget!', 'success');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to book hotel', 'error');
    }
}

async function openEditHotelModal(bookingId) {
    if (!state.currentTrip) return;
    const hotel = (state.currentTrip.hotels || []).find(h => h.id === bookingId);
    if (!hotel) {
        showToast('Booking details not found', 'error');
        return;
    }

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-pen"></i> Edit Hotel Stay: ${escapeHtml(hotel.hotel_name)}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleConfirmEditHotel(${bookingId});">
            <div class="modal-body">
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Check-in Date</label>
                        <input type="date" id="edit-hotel-in" class="form-control" value="${hotel.check_in}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Check-out Date</label>
                        <input type="date" id="edit-hotel-out" class="form-control" value="${hotel.check_out}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Number of Rooms</label>
                        <input type="number" id="edit-hotel-rooms" min="1" max="10" class="form-control" value="${hotel.number_of_rooms || 1}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Number of Guests</label>
                        <input type="number" id="edit-hotel-guests" min="1" max="20" class="form-control" value="${hotel.number_of_guests || 2}">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Room Type</label>
                    <input type="text" id="edit-hotel-roomtype" class="form-control" value="${escapeHtml(hotel.room_type_selected || 'Standard Double Room')}">
                </div>
                <div class="form-group">
                    <label class="form-label">Booking Notes</label>
                    <textarea id="edit-hotel-notes" class="form-control" rows="2">${escapeHtml(hotel.notes || '')}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Reservation</button>
            </div>
        </form>
    `);
}

async function handleConfirmEditHotel(bookingId) {
    if (!state.currentTrip) return;
    const checkIn = document.getElementById('edit-hotel-in').value;
    const checkOut = document.getElementById('edit-hotel-out').value;
    const rooms = parseInt(document.getElementById('edit-hotel-rooms').value) || 1;
    const guests = parseInt(document.getElementById('edit-hotel-guests').value) || 2;
    const roomType = document.getElementById('edit-hotel-roomtype').value.trim();
    const notes = document.getElementById('edit-hotel-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${state.currentTrip.id}/hotels/${bookingId}`, 'PUT', {
        check_in: checkIn,
        check_out: checkOut,
        number_of_rooms: rooms,
        number_of_guests: guests,
        room_type_selected: roomType,
        notes: notes
    });

    if (res.success) {
        closeModal();
        showToast('Hotel reservation updated!', 'success');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to update reservation', 'error');
    }
}

async function handleDeleteHotelBooking(bookingId) {
    if (!state.currentTrip) return;
    if (!confirm('Are you sure you want to remove this hotel accommodation?')) return;

    const res = await apiRequest(`/api/v1/trips/${state.currentTrip.id}/hotels/${bookingId}`, 'DELETE');
    if (res.success) {
        showToast('Hotel removed and budget updated.', 'info');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to remove hotel', 'error');
    }
}

// ================= App Initialization =================
window.addEventListener('DOMContentLoaded', async () => {
    // Check if initial URL is a public shared route
    const path = window.location.pathname;
    if (path.startsWith('/shared/')) {
        const token = path.split('/shared/')[1];
        state.sharedToken = token;
        await initAuth();
        navigateTo('shared', token);
        return;
    }

    await initAuth();
    navigateTo('dashboard');
});

