"use client";

import { useState, useRef, FormEvent, ChangeEvent } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Terminal } from 'lucide-react';

type AuthState = 'idle' | 'pending-2fa' | 'pending-mobile' | 'loading' | 'success' | 'error';

export default function AuthPage() {
  const [authState, setAuthState] = useState<AuthState>('idle');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [twoFaCode, setTwoFaCode] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setAuthState('loading');
    setFeedbackMessage('Attempting to log in...');
    try {
      const response = await fetch('/api/auth/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (response.ok) {
        if (data.status === '2fa_required') {
          setAuthState('pending-2fa');
          setFeedbackMessage('Two-factor authentication required. Please enter the code sent to your device.');
        } else if (data.status === '2fa_mobile_required') {
          setAuthState('pending-mobile');
          setFeedbackMessage('Check your mobile device! LinkedIn sent a notification. Click "Yes" on your phone.');
        } else if (data.status === 'success') {
          setAuthState('success');
          setFeedbackMessage('Authentication successful! The auth_state.json has been generated.');
        }
      } else {
        throw new Error(data.detail || 'Failed to log in.');
      }
    } catch (error: any) {
      setAuthState('error');
      setFeedbackMessage(error.message);
    }
  };

  const handleVerify2FA = async (e: FormEvent) => {
    e.preventDefault();
    setAuthState('loading');
    setFeedbackMessage('Verifying...');
    try {
      // If we are in mobile pending state, we don't send a code
      const body = authState === 'pending-mobile' ? {} : { code: twoFaCode };

      const response = await fetch('/api/auth/verify-2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json();

      if (response.ok) {
        if (data.status === 'success') {
          setAuthState('success');
          setFeedbackMessage('Verification successful! The auth_state.json has been generated.');
        } else if (data.status === 'waiting_for_approval') {
          setAuthState('pending-mobile');
          setFeedbackMessage('Still waiting for approval on phone... Please try "I approved" again.');
        }
      } else {
        throw new Error(data.detail || 'Failed to verify.');
      }
    } catch (error: any) {
      setAuthState('error');
      setFeedbackMessage(error.message);
    }
  };

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAuthState('loading');
    setFeedbackMessage(`Uploading ${file.name}...`);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/auth/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        setAuthState('success');
        setFeedbackMessage(`Successfully uploaded and saved ${file.name}.`);
      } else {
        throw new Error(data.detail || 'File upload failed.');
      }
    } catch (error: any) {
      setAuthState('error');
      setFeedbackMessage(error.message);
    }
  };

  const renderFeedback = () => {
    if (!feedbackMessage) return null;
    const variant = authState === 'error' ? 'destructive' : 'default';
    return (
      <Alert variant={variant} className="mt-4">
        <Terminal className="h-4 w-4" />
        <AlertTitle>
          {authState === 'loading' && 'In Progress'}
          {authState === 'success' && 'Success'}
          {authState === 'error' && 'Error'}
          {(authState === 'pending-2fa' || authState === 'pending-mobile') && 'Action Required'}
        </AlertTitle>
        <AlertDescription>
          {feedbackMessage}
        </AlertDescription>
      </Alert>
    );
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">LinkedIn Authentication</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Automated Login</CardTitle>
            <CardDescription>Enter your LinkedIn credentials to generate the authentication file automatically.</CardDescription>
          </CardHeader>
          <CardContent>
            {authState === 'pending-2fa' ? (
              <form onSubmit={handleVerify2FA}>
                <div>
                  <label htmlFor="2fa">Verification Code</label>
                  <Input id="2fa" type="text" placeholder="Enter 6-digit code" value={twoFaCode} onChange={(e) => setTwoFaCode(e.target.value)} disabled={authState === 'loading' || authState === 'success'} />
                </div>
                <Button type="submit" className="mt-4 w-full" disabled={authState === 'loading' || authState === 'success'}>
                  {authState === 'loading' ? 'Verifying...' : 'Verify'}
                </Button>
              </form>
            ) : authState === 'pending-mobile' ? (
              <div className="text-center py-4">
                 <p className="mb-4 text-sm text-slate-500">Please open the LinkedIn app on your mobile device and approve the login request.</p>
                 <Button onClick={handleVerify2FA} className="w-full" disabled={authState === 'loading'}>
                  {authState === 'loading' ? 'Checking...' : 'I have approved'}
                </Button>
              </div>
            ) : (
              <form onSubmit={handleLogin}>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="email">Email</label>
                    <Input id="email" type="email" placeholder="email@example.com" value={email} onChange={(e) => setEmail(e.target.value)} disabled={authState === 'loading' || authState === 'success'} />
                  </div>
                  <div>
                    <label htmlFor="password">Password</label>
                    <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={authState === 'loading' || authState === 'success'} />
                  </div>
                </div>
                <Button type="submit" className="mt-4 w-full" disabled={authState === 'loading' || authState === 'success'}>
                  {authState === 'loading' ? 'Connecting...' : 'Connect'}
                </Button>
              </form>
            )}
          </CardContent>
          <CardFooter>
            {renderFeedback()}
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Manual Upload</CardTitle>
            <CardDescription>If you already have an `auth_state.json` file, you can upload it directly.</CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              type="file"
              accept=".json"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button onClick={() => fileInputRef.current?.click()} className="w-full" variant="outline" disabled={authState === 'loading'}>
              Upload auth_state.json
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
