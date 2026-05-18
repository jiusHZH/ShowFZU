import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { forgotPasswordReset, forgotPasswordStart, register } from '@/lib/api'
import { useAuth } from '@/context/useAuth'
import type { LoginMethod } from '@/types/api'

function getReturnTarget(searchParams: URLSearchParams) {
  return searchParams.get('returnTo') || '/profile'
}

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()

  const [loginMethod, setLoginMethod] = useState<LoginMethod>('account_id')
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const helperText = useMemo(
    () =>
      loginMethod === 'account_id'
        ? 'Use the immutable 8 to 12 digit Account ID.'
        : 'Use the public username exactly as it appears on profile pages.',
    [loginMethod],
  )

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      await login({
        login_method: loginMethod,
        identifier,
        password,
      })
      navigate(getReturnTarget(searchParams), { replace: true })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Login failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-panel auth-panel--accent">
        <span className="eyebrow">Sign in</span>
        <h1>Choose the identifier type first, then enter your password.</h1>
        <p>
          Numeric usernames are allowed in ShowFZU, so login mode must stay explicit. The site will not auto-detect whether an identifier is an Account ID or a Username.
        </p>
      </section>
      <section className="auth-panel">
        <form className="stack-md" onSubmit={(event) => void handleSubmit(event)}>
          <div className="segmented-control">
            <button
              className={loginMethod === 'account_id' ? 'is-active' : ''}
              onClick={() => setLoginMethod('account_id')}
              type="button"
            >
              Account ID
            </button>
            <button
              className={loginMethod === 'username' ? 'is-active' : ''}
              onClick={() => setLoginMethod('username')}
              type="button"
            >
              Username
            </button>
          </div>
          <label className="field">
            <span>{loginMethod === 'account_id' ? 'Account ID' : 'Username'}</span>
            <input
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder={loginMethod === 'account_id' ? '12345678' : 'Campus Storyteller'}
            />
            <small>{helperText}</small>
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <p className="error-banner">{error}</p> : null}
          <button className="button button--primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Signing in…' : 'Login'}
          </button>
          <div className="auth-links">
            <Link to="/register">Create an account</Link>
            <Link to="/forgot-password">Forgot password?</Link>
          </div>
        </form>
      </section>
    </div>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    account_id: '',
    username: '',
    password: '',
    confirm_password: '',
    security_question: '',
    security_answer: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      await register(form)
      navigate('/login')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Registration failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-panel auth-panel--accent">
        <span className="eyebrow">Register</span>
        <h1>Set up a campus account with both an Account ID and a public username.</h1>
        <p>
          Account ID is private, immutable, and only for the account owner. Username stays public and can be changed later.
        </p>
      </section>
      <section className="auth-panel">
        <form className="stack-md" onSubmit={(event) => void handleSubmit(event)}>
          {[
            ['account_id', 'Account ID'],
            ['username', 'Username'],
            ['security_question', 'Security question'],
            ['security_answer', 'Security answer'],
          ].map(([name, label]) => (
            <label key={name} className="field">
              <span>{label}</span>
              <input
                value={form[name as keyof typeof form]}
                onChange={(event) =>
                  setForm((current) => ({ ...current, [name]: event.target.value }))
                }
              />
            </label>
          ))}
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Confirm password</span>
            <input
              type="password"
              value={form.confirm_password}
              onChange={(event) =>
                setForm((current) => ({ ...current, confirm_password: event.target.value }))
              }
            />
          </label>
          {error ? <p className="error-banner">{error}</p> : null}
          <button className="button button--primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Creating account…' : 'Register'}
          </button>
          <div className="auth-links">
            <Link to="/login">Already have an account?</Link>
          </div>
        </form>
      </section>
    </div>
  )
}

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [accountId, setAccountId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await forgotPasswordStart(accountId)
      navigate(
        `/reset-password?accountId=${encodeURIComponent(accountId)}&question=${encodeURIComponent(response.security_question)}`,
      )
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not start password reset.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-panel auth-panel--accent">
        <span className="eyebrow">Forgot password</span>
        <h1>Start recovery with the private Account ID.</h1>
        <p>Password recovery is intentionally tied to Account ID only, not the public username.</p>
      </section>
      <section className="auth-panel">
        <form className="stack-md" onSubmit={(event) => void handleSubmit(event)}>
          <label className="field">
            <span>Account ID</span>
            <input value={accountId} onChange={(event) => setAccountId(event.target.value)} />
          </label>
          {error ? <p className="error-banner">{error}</p> : null}
          <button className="button button--primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Checking…' : 'Show security question'}
          </button>
        </form>
      </section>
    </div>
  )
}

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const accountId = searchParams.get('accountId') ?? ''
  const question = searchParams.get('question') ?? ''
  const [form, setForm] = useState({
    security_answer: '',
    new_password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    try {
      const response = await forgotPasswordReset({
        account_id: accountId,
        ...form,
      })
      setMessage(response.message)
      setTimeout(() => navigate('/login'), 1000)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Password reset failed.')
    }
  }

  if (!accountId || !question) {
    return (
      <div className="page-intro">
        <span className="eyebrow">Reset password</span>
        <h1>Password recovery needs a valid Account ID and question first.</h1>
        <Link className="button button--primary" to="/forgot-password">
          Restart recovery
        </Link>
      </div>
    )
  }

  return (
    <div className="auth-layout">
      <section className="auth-panel auth-panel--accent">
        <span className="eyebrow">Reset password</span>
        <h1>Answer your custom security question.</h1>
        <p>{question}</p>
      </section>
      <section className="auth-panel">
        <form className="stack-md" onSubmit={(event) => void handleSubmit(event)}>
          <label className="field">
            <span>Security answer</span>
            <input
              value={form.security_answer}
              onChange={(event) => setForm((current) => ({ ...current, security_answer: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>New password</span>
            <input
              type="password"
              value={form.new_password}
              onChange={(event) => setForm((current) => ({ ...current, new_password: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Confirm new password</span>
            <input
              type="password"
              value={form.confirm_password}
              onChange={(event) =>
                setForm((current) => ({ ...current, confirm_password: event.target.value }))
              }
            />
          </label>
          {message ? <p className="success-banner">{message}</p> : null}
          {error ? <p className="error-banner">{error}</p> : null}
          <button className="button button--primary" type="submit">
            Reset password
          </button>
        </form>
      </section>
    </div>
  )
}
