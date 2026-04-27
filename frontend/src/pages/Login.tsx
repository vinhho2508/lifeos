import React, { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  const handleCallbackResponse = useCallback(async (response: { credential: string }) => {
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
        alert(axiosErr.response?.data?.detail || 'Unauthorized account')
      } else {
        alert('Login failed')
      }
    }
  }, [navigate])

  useEffect(() => {
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCallbackResponse,
      })

      window.google.accounts.id.renderButton(
        document.getElementById('signInDiv'),
        { theme: 'outline', size: 'large' }
      )
    }
  }, [clientId, handleCallbackResponse])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>LifeOS Login</CardTitle>
          <CardDescription>Sign in with your Google account</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <div id="signInDiv"></div>
          <p className="text-sm text-muted-foreground">
            Only vinhho2508@gmail.com is authorized.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export default Login
