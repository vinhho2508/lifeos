import React, { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { Card, toast } from '@heroui/react'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  const handleCallbackResponse = useCallback(
    async (response: { credential: string }) => {
      try {
        const res = await api.post('/auth/login', {
          token: response.credential,
        })

        localStorage.setItem('token', res.data.access_token)
        navigate('/chat')
      } catch (err: unknown) {
        console.error('Login failed:', err)
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { data?: { detail?: string } } }
          toast.danger(axiosErr.response?.data?.detail || 'Unauthorized account')
        } else {
          toast.danger('Login failed')
        }
      }
    },
    [navigate],
  )

  useEffect(() => {
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCallbackResponse,
      })

      window.google.accounts.id.renderButton(document.getElementById('signInDiv'), {
        theme: 'outline',
        size: 'large',
      })
    }
  }, [clientId, handleCallbackResponse])

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm items-center gap-6 p-8 text-center">
        <div className="flex size-10 items-center justify-center rounded-xl bg-accent text-lg font-semibold text-accent-foreground">
          L
        </div>
        <Card.Header className="items-center">
          <Card.Title className="text-lg">Welcome to LifeOS</Card.Title>
          <Card.Description>Sign in with your Google account to continue.</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col items-center gap-4">
          <div id="signInDiv"></div>
          <p className="text-xs text-muted">Only vinhho2508@gmail.com is authorized.</p>
        </Card.Content>
      </Card>
    </div>
  )
}

export default Login
