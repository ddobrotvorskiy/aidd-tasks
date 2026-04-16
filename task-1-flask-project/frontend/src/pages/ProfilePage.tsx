import { UploadOutlined } from '@ant-design/icons';
import {
  Alert,
  Avatar,
  Button,
  Card,
  Form,
  Input,
  Spin,
  Typography,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import React, { useEffect, useState } from 'react';
import { changePassword, updateMyProfile, uploadPhoto } from '../api/employees';
import { useMyProfile } from '../hooks/useEmployees';
import type { ChangePasswordPayload, ProfileUpdatePayload } from '../types';
import { useQueryClient } from '@tanstack/react-query';

const ProfilePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useMyProfile();
  const [profileForm] = Form.useForm();
  const [pwForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);

  useEffect(() => {
    if (profile) {
      profileForm.setFieldsValue({
        full_name: profile.full_name,
        job_title: profile.job_title ?? '',
        department: profile.department ?? '',
        phone: profile.phone ?? '',
      });
    }
  }, [profile, profileForm]);

  const handleProfileSave = async (values: ProfileUpdatePayload) => {
    setError(null);
    setSaving(true);
    try {
      await updateMyProfile(values);
      await queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      message.success('Profile updated');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        'Update failed';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (file: UploadFile) => {
    if (!file.originFileObj) return;
    try {
      await uploadPhoto(file.originFileObj);
      await queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      message.success('Photo updated');
    } catch {
      message.error('Photo upload failed');
    }
    return false; // prevent default upload
  };

  const handlePasswordChange = async (values: ChangePasswordPayload) => {
    setPwError(null);
    setPwSaving(true);
    try {
      await changePassword(values);
      message.success('Password changed');
      pwForm.resetFields();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        'Failed to change password';
      setPwError(msg);
    } finally {
      setPwSaving(false);
    }
  };

  if (isLoading) return <Spin size="large" />;

  return (
    <div style={{ maxWidth: 600 }}>
      <Typography.Title level={2}>My Profile</Typography.Title>

      {/* Avatar section */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <Avatar
            size={96}
            src={profile?.photo_url ?? undefined}
            style={{ backgroundColor: '#1677ff' }}
          >
            {profile?.full_name?.charAt(0).toUpperCase()}
          </Avatar>
          <Upload
            accept="image/*"
            showUploadList={false}
            beforeUpload={(file) => {
              handlePhotoUpload({ originFileObj: file } as UploadFile);
              return false;
            }}
          >
            <Button icon={<UploadOutlined />}>Change Photo</Button>
          </Upload>
        </div>
      </Card>

      {/* Profile form */}
      <Card title="Profile Information" style={{ marginBottom: 24 }}>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Form form={profileForm} layout="vertical" onFinish={handleProfileSave}>
          <Form.Item
            label="Full Name"
            name="full_name"
            rules={[{ required: true, message: 'Full name is required' }]}
          >
            <Input />
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
            <Button type="primary" htmlType="submit" loading={saving}>
              Save Changes
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Change password */}
      <Card title="Change Password">
        {pwError && <Alert type="error" message={pwError} style={{ marginBottom: 16 }} />}
        <Form form={pwForm} layout="vertical" onFinish={handlePasswordChange}>
          <Form.Item
            label="Current Password"
            name="current_password"
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label="New Password"
            name="new_password"
            rules={[{ required: true, min: 8, message: 'At least 8 characters' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button htmlType="submit" loading={pwSaving}>
              Change Password
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default ProfilePage;
