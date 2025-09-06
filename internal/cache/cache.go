package cache

import (
	"fmt"
	"sync"
)

type Cache[K comparable, V any] struct {
	lock      sync.RWMutex
	expiredFn func(cached V) bool
	cached    map[K]V
}

func NewCache[K comparable, V any](expiredFn func(cached V) bool) *Cache[K, V] {
	return &Cache[K, V]{
		expiredFn: expiredFn,
		cached:    map[K]V{},
	}
}

func (c *Cache[K, V]) Store(key K, value V) {
	c.lock.Lock()
	defer c.lock.Unlock()

	c.cached[key] = value
}

func (c *Cache[K, V]) Get(key K, fetchFn func() (V, error)) (V, error) {
	if cached, ok := c.getCached(key); ok {
		return cached, nil
	}

	c.lock.Lock()
	defer c.lock.Unlock()

	v, err := fetchFn()
	if err != nil {
		return v, fmt.Errorf("fetching cache value: %w", err)
	}

	c.cached[key] = v

	return v, nil
}

func (c *Cache[K, V]) getCached(key K) (V, bool) {
	c.lock.RLock()
	defer c.lock.RUnlock()

	var zero V
	cached, ok := c.cached[key]
	if !ok {
		return zero, false
	}

	if c.expiredFn(cached) {
		return cached, false
	}

	return cached, true
}

func (c *Cache[K, V]) Clear(key K) {
	c.lock.Lock()
	defer c.lock.Unlock()
	delete(c.cached, key)
}
