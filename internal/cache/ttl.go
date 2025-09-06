package cache

import (
	"time"
)

type ttlEntry[V any] struct {
	value        V
	expiresAtUtc time.Time
}

type TtlCache[K comparable, V any] struct {
	ttl   time.Duration
	cache Cache[K, *ttlEntry[V]]

	TimeFn func() time.Time
}

func NewTtlCache[K comparable, V any](ttl time.Duration) *TtlCache[K, V] {
	c := &TtlCache[K, V]{
		ttl: ttl,
		cache: Cache[K, *ttlEntry[V]]{
			cached: map[K]*ttlEntry[V]{},
		},
		TimeFn: func() time.Time {
			return time.Now().UTC()
		},
	}

	c.cache.expiredFn = func(cached *ttlEntry[V]) bool {
		return c.TimeFn().After(cached.expiresAtUtc)
	}

	return c
}

func (c *TtlCache[K, V]) Get(key K, fetchFn func() (V, error)) (V, error) {
	var zero V
	v, err := c.cache.Get(key, func() (*ttlEntry[V], error) {
		v, err := fetchFn()
		if err != nil {
			return &ttlEntry[V]{}, err
		}

		return &ttlEntry[V]{
			value:        v,
			expiresAtUtc: c.TimeFn().Add(c.ttl),
		}, nil
	})
	if err != nil {
		return zero, err
	}

	return v.value, err
}

func (c *TtlCache[K, V]) Clear(key K) {
	c.cache.Clear(key)
}
