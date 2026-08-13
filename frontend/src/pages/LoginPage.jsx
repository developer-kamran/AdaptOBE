import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { Card, CardBody } from '../components/ui/Card'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const user = await login(email, password)
      const destination =
        user?.role === 'super_admin' || user?.role === 'sub_admin'
          ? '/admin'
          : user?.role === 'faculty'
            ? '/dashboard'
            : '/courses'
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-lg mb-3">
            A
          </div>
          <h1 className="text-lg font-semibold text-ink-900">AdaptOBE</h1>
          <p className="text-sm text-ink-500 mt-0.5">Sign in to your faculty dashboard</p>
        </div>

        <Card>
          <CardBody>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <Input
                id="email"
                type="email"
                label="Email"
                placeholder="you@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                required
              />
              <Input
                id="password"
                type="password"
                label="Password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              {error && (
                <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}
              <Button type="submit" isLoading={isSubmitting} className="w-full mt-1">
                Sign in
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
