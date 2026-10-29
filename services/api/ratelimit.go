package main

import (
	"math"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type clientBucket struct {
	tokens     float64
	lastRefill time.Time
}

type RateLimiter struct {
	mu      sync.Mutex
	buckets map[string]*clientBucket
}

func NewRateLimiter() *RateLimiter {
	rl := &RateLimiter{
		buckets: make(map[string]*clientBucket),
	}
	// Limpeza periódica de baldes inativos
	go func() {
		ticker := time.NewTicker(5 * time.Minute)
		for range ticker.C {
			rl.cleanup(10 * time.Minute)
		}
	}()
	return rl
}

func (rl *RateLimiter) cleanup(maxAge time.Duration) {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	now := time.Now()
	for k, b := range rl.buckets {
		if now.Sub(b.lastRefill) > maxAge {
			delete(rl.buckets, k)
		}
	}
}

// Allow verifica se a requisição pode prosseguir dentro da cota configurada (rpm: requests per minute).
func (rl *RateLimiter) Allow(key string, limitRPM int) (bool, int, time.Duration) {
	if limitRPM <= 0 {
		return true, limitRPM, 0
	}

	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	capacity := float64(limitRPM)
	refillRate := capacity / 60.0 // tokens por segundo

	b, exists := rl.buckets[key]
	if !exists {
		rl.buckets[key] = &clientBucket{
			tokens:     capacity - 1.0,
			lastRefill: now,
		}
		return true, int(capacity - 1.0), 0
	}

	// Reabastece tokens proporcionais ao tempo decorrido
	elapsed := now.Sub(b.lastRefill).Seconds()
	b.tokens = math.Min(capacity, b.tokens+(elapsed*refillRate))
	b.lastRefill = now

	if b.tokens >= 1.0 {
		b.tokens -= 1.0
		return true, int(b.tokens), 0
	}

	// Balde vazio: calcula tempo para ter pelo menos 1 token
	missing := 1.0 - b.tokens
	retrySeconds := missing / refillRate
	if retrySeconds < 1.0 {
		retrySeconds = 1.0
	}

	return false, 0, time.Duration(math.Ceil(retrySeconds)) * time.Second
}

func getClientKey(r *http.Request, auth AuthContext) string {
	if auth.IsAuthenticated && auth.ActorID != "" {
		return "actor:" + auth.ActorID
	}
	// Fallback para IP remoto
	forwarded := r.Header.Get("X-Forwarded-For")
	if forwarded != "" {
		parts := strings.Split(forwarded, ",")
		return "ip:" + strings.TrimSpace(parts[0])
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err == nil && host != "" {
		return "ip:" + host
	}
	return "ip:" + r.RemoteAddr
}

func getRateLimitForRole(role ActorRole) int {
	switch role {
	case RolePublisher:
		return 300 // 300 req/min
	case RoleReviewer:
		return 200 // 200 req/min
	case RoleProducer:
		return 120 // 120 req/min
	default:
		return 60 // 60 req/min para visitante público
	}
}

func (a *API) checkRateLimit(w http.ResponseWriter, r *http.Request, auth AuthContext) bool {
	if a.rateLimiter == nil {
		return true
	}

	key := getClientKey(r, auth)
	limitRPM := getRateLimitForRole(auth.Role)

	// Permite override de teste via header estritamente em ambiente de teste configurado
	if os.Getenv("BDF_ENABLE_TEST_RATE_LIMIT") == "1" {
		if testLimit := r.Header.Get("X-Test-Rate-Limit-RPM"); testLimit != "" {
			if val, err := strconv.Atoi(testLimit); err == nil && val > 0 {
				limitRPM = val
			}
		}
	}

	allowed, remaining, retryAfter := a.rateLimiter.Allow(key, limitRPM)

	w.Header().Set("X-RateLimit-Limit", strconv.Itoa(limitRPM))
	w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))

	if !allowed {
		retrySec := int(retryAfter.Seconds())
		if retrySec < 1 {
			retrySec = 1
		}
		w.Header().Set("Retry-After", strconv.Itoa(retrySec))
		write(w, http.StatusTooManyRequests, map[string]any{
			"error":       "rate limit exceeded",
			"retry_after": retrySec,
			"limit_rpm":   limitRPM,
		})
		return false
	}

	return true
}
