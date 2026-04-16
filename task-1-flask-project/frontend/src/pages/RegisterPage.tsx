import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import type { RegisterPayload } from '../types';

const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: RegisterPayload) => {
    setError(null);
    setLoading(true);
    try {
      await register(values);
      navigate('/employees');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        'Registration failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
      <Card style={{ width: 480 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          Create Account
        </Typography.Title>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="Full Name"
            name="full_name"
            rules={[{ required: true, message: 'Enter your full name' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Email"
            name="email"
            rules={[{ required: true, type: 'email', message: 'Enter a valid email' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, min: 8, message: 'At least 8 characters' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item label="Job Title" name="job_title">
            <Input />
          </Form.Item>
          <Form.Item label="Department" name="department">
            <Input />
          </Form.Item>
          <Form.Item label="Phone" name="phone">
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Register
            </Button>
          </Form.Item>
        </Form>
        <Typography.Text>
          Already have an account? <Link to="/login">Login</Link>
        </Typography.Text>
      </Card>
    </div>
  );
};

export default RegisterPage;
