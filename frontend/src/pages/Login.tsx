import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  useEffect(() => {
    /* global google */
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
  }, [clientId])

  const handleCallbackResponse = async (response: any) => {
    try {
      const res = await api.post('/auth/login', {
        token: response.credential,
      })
      
      localStorage.setItem('token', res.data.access_token)
      navigate('/')
    } catch (err: any) {
      console.error('Login failed:', err)
      alert(err.response?.data?.detail || 'Unauthorized account')
    }
  }

  return (
    <div className="login-container">
      <h1>LifeOS Login</h1>
      <div id="signInDiv"></div>
      <p style={{ marginTop: '20px', color: '#888' }}>
        Only vinhho2508@gmail.com is authorized.
      </p>
    </div>
  )
}

export default Login
