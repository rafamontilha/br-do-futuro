package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
)

type ActorRole string

const (
	RolePublic    ActorRole = "public"
	RoleProducer  ActorRole = "producer"
	RoleReviewer  ActorRole = "reviewer"
	RolePublisher ActorRole = "publisher"
)

type AuthContext struct {
	ActorID         string    `json:"actor_id"`
	ActorName       string    `json:"actor_name"`
	Role            ActorRole `json:"role"`
	IsAuthenticated bool      `json:"is_authenticated"`
}

func parseBearerToken(r *http.Request) string {
	if apiKey := r.Header.Get("X-API-Key"); apiKey != "" {
		return strings.TrimSpace(apiKey)
	}
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return ""
	}
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) == 2 && strings.EqualFold(parts[0], "bearer") {
		return strings.TrimSpace(parts[1])
	}
	return ""
}

func (a *API) authenticate(r *http.Request) AuthContext {
	token := parseBearerToken(r)
	if token != "" {
		// Tokens canônicos conhecidos de desenvolvimento e teste
		switch token {
		case "bdf-producer-token-2026":
			return AuthContext{
				ActorID:         "user-producer-01",
				ActorName:       "Produtor Oficial de Dados",
				Role:            RoleProducer,
				IsAuthenticated: true,
			}
		case "bdf-reviewer-token-2026":
			return AuthContext{
				ActorID:         "user-reviewer-01",
				ActorName:       "Revisor Metodológico Independente",
				Role:            RoleReviewer,
				IsAuthenticated: true,
			}
		case "bdf-publisher-token-2026":
			return AuthContext{
				ActorID:         "user-publisher-01",
				ActorName:       "Publicador de Políticas e Guidance",
				Role:            RolePublisher,
				IsAuthenticated: true,
			}
		}

		// Checagem de token dinâmico no banco de dados via hash SHA-256
		if a.db != nil {
			h := sha256.Sum256([]byte(token))
			tokenHash := hex.EncodeToString(h[:])
			var actorID, actorName, role string
			var isActive bool
			err := a.db.QueryRow(r.Context(),
				"SELECT actor_id, actor_name, role, is_active FROM system_api_keys WHERE token_hash = $1",
				tokenHash,
			).Scan(&actorID, &actorName, &role, &isActive)
			if err == nil && isActive {
				return AuthContext{
					ActorID:         actorID,
					ActorName:       actorName,
					Role:            ActorRole(role),
					IsAuthenticated: true,
				}
			}
		}
	}

	// Cabeçalhos de contexto de teste e simulação local (X-Actor-Role, X-Actor-Id)
	roleHeader := strings.ToLower(strings.TrimSpace(r.Header.Get("X-Actor-Role")))
	if roleHeader != "" {
		actorID := r.Header.Get("X-Actor-Id")
		if actorID == "" {
			actorID = "simulated-" + roleHeader
		}
		switch ActorRole(roleHeader) {
		case RoleProducer:
			return AuthContext{ActorID: actorID, ActorName: "Simulated Producer", Role: RoleProducer, IsAuthenticated: true}
		case RoleReviewer:
			return AuthContext{ActorID: actorID, ActorName: "Simulated Reviewer", Role: RoleReviewer, IsAuthenticated: true}
		case RolePublisher:
			return AuthContext{ActorID: actorID, ActorName: "Simulated Publisher", Role: RolePublisher, IsAuthenticated: true}
		}
	}

	return AuthContext{
		ActorID:         "anonymous",
		ActorName:       "Público Visitante",
		Role:            RolePublic,
		IsAuthenticated: false,
	}
}

func roleWeight(r ActorRole) int {
	switch r {
	case RolePublic:
		return 0
	case RoleProducer:
		return 10
	case RoleReviewer:
		return 20
	case RolePublisher:
		return 30
	default:
		return -1
	}
}

func requireRole(w http.ResponseWriter, auth AuthContext, minRole ActorRole) bool {
	if !auth.IsAuthenticated {
		write(w, http.StatusUnauthorized, map[string]string{
			"error": "unauthorized: authentication credentials required",
		})
		return false
	}

	if roleWeight(auth.Role) < roleWeight(minRole) {
		write(w, http.StatusForbidden, map[string]string{
			"error": "forbidden: insufficient permissions for role " + string(auth.Role),
		})
		return false
	}

	return true
}

func verifyActorRoleInDB(ctx context.Context, db *pgxpool.Pool, actorID string, expectedRole ActorRole) bool {
	if db == nil {
		return false
	}
	var role string
	err := db.QueryRow(ctx, "SELECT role FROM system_api_keys WHERE actor_id = $1 AND is_active = true", actorID).Scan(&role)
	return err == nil && ActorRole(role) == expectedRole
}
