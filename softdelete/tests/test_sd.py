from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db import models
from softdelete.test_softdelete_app.models import (
    TestModelOne,
    TestModelTwo,
    TestModelThree,
    TestModelThrough,
    TestModelSafeDeleteCascade,
    TestModelSoftDelete,
    TestModelDefault,
    TestModelSoftDeleteOnRelationLevelParent,
    TestModelSoftDeleteOnRelationLevelChild,
    TestModelSoftDeleteOnRelationLevelSecondChild,
    TestModelSoftDeleteOnRelationLevelChildSetNull,
    TestModelOneToOneRelationWithNonSoftDeleteObject
)
from softdelete.models import *
from softdelete.signals import *
import logging
try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse


class BaseTest(TestCase):
    def setUp(self):
        self.tmo1 = TestModelOne.objects.create(extra_bool=True)
        self.tmo2 = TestModelOne.objects.create(extra_bool=False)
        for x in range(10):
            if x % 2:
                parent = self.tmo1
            else:
                parent = self.tmo2
            TestModelTwo.objects.create(extra_int=x, tmo=parent)
        for x in range(10):
            if x % 2:
                left_side = self.tmo1
            else:
                left_side = self.tmo2
            for x in range(10):
                t3 = TestModelThree.objects.create()
                tmt = TestModelThrough.objects.create(tmo1=left_side, tmo3=t3)
        self.user = User.objects.create_user(username='SoftdeleteUser',
                                             password='SoftdeletePassword',
                                             email='softdeleteuser@example.com')
        gr = create_group()
        if USE_SOFTDELETE_GROUP:
            gr = Group.objects.get(name="Softdelete User")
            self.user.groups.add(gr)
            self.user.save()
            gr.save()
        else:
            assign_permissions(self.user)
        self.user.save()
        self.unauthorized = User.objects.create_user(username='NonSoftdeleteUser',
                                                     password='NonSoftdeletePassword',
                                                     email='nonsoftdeleteuser@example.com')
        ## Setup for delete policy tests
        self.tmo_soft_delete_cascade = TestModelSafeDeleteCascade.objects.create(
            extra_int=100)
        self.tmo_soft_delete = TestModelSoftDelete.objects.create(
            parent=self.tmo_soft_delete_cascade)
        self.tmo_delete_default = TestModelDefault.objects.create(
            parent=self.tmo_soft_delete)
        self.tmo_soft_delete_relation_parent = TestModelSoftDeleteOnRelationLevelParent.objects.create(
            extra_int=100
        )
        self.tmo_soft_delete_relation_child = TestModelSoftDeleteOnRelationLevelChild.objects.create(
            parent=self.tmo_soft_delete_relation_parent
        )
        self.tmo_soft_delete_relation_second_child = TestModelSoftDeleteOnRelationLevelSecondChild.objects.create(
            parent=self.tmo_soft_delete_relation_parent
        )
        self.tmo_soft_delete_relation_child_set_null = TestModelSoftDeleteOnRelationLevelChildSetNull.objects.create(
            parent=self.tmo_soft_delete_relation_parent
        )
        self.tmo_non_soft_delete_one_to_one = TestModelOneToOneRelationWithNonSoftDeleteObject.objects.create(
            one_to_one=self.tmo_soft_delete_relation_parent
        )


class InitialTest(BaseTest):

    def test_simple_delete(self):
        self.assertEquals(2, TestModelOne.objects.count())
        self.assertEquals(10, TestModelTwo.objects.count())
        self.assertEquals(2,
                          TestModelOne.objects.all_with_deleted().count())
        self.assertEquals(10,
                          TestModelTwo.objects.all_with_deleted().count())
        self.tmo1.delete()
        self.assertEquals(1, TestModelOne.objects.count())
        self.assertEquals(5, TestModelTwo.objects.count())
        self.assertEquals(2,
                          TestModelOne.objects.all_with_deleted().count())
        self.assertEquals(10,
                          TestModelTwo.objects.all_with_deleted().count())

class DeleteTest(BaseTest):
    def pre_delete(self, *args, **kwargs):
        self.pre_delete_called = True

    def post_delete(self, *args, **kwargs):
        self.post_delete_called = True

    def pre_soft_delete(self, *args, **kwargs):
        self.pre_soft_delete_called = True

    def post_soft_delete(self, *args, **kwargs):
        self.post_soft_delete_called = True

    def _pretest(self):
        self.pre_delete_called = False
        self.post_delete_called = False
        self.pre_soft_delete_called = False
        self.post_soft_delete_called = False
        models.signals.pre_delete.connect(self.pre_delete)
        models.signals.post_delete.connect(self.post_delete)
        pre_soft_delete.connect(self.pre_soft_delete)
        post_soft_delete.connect(self.post_soft_delete)
        self.assertEquals(2, TestModelOne.objects.count())
        self.assertEquals(10, TestModelTwo.objects.count())
        self.assertFalse(self.tmo1.deleted)
        self.assertFalse(self.pre_delete_called)
        self.assertFalse(self.post_delete_called)
        self.assertFalse(self.pre_soft_delete_called)
        self.assertFalse(self.post_soft_delete_called)
        self.cs_count = ChangeSet.objects.count()
        self.rs_count = SoftDeleteRecord.objects.count()

    def _posttest(self):
        self.tmo1 = TestModelOne.objects.all_with_deleted().get(pk=self.tmo1.pk)
        self.tmo2 = TestModelOne.objects.all_with_deleted().get(pk=self.tmo2.pk)
        self.assertTrue(self.tmo1.deleted)
        self.assertFalse(self.tmo2.deleted)
        self.assertTrue(self.pre_delete_called)
        self.assertTrue(self.post_delete_called)
        self.assertTrue(self.pre_soft_delete_called)
        self.assertTrue(self.post_soft_delete_called)
        self.tmo1.undelete()

    def test_delete(self):
        self._pretest()
        self.tmo1.delete()
        self.assertEquals(self.cs_count+1, ChangeSet.objects.count())
        self.assertEquals(self.rs_count+56, SoftDeleteRecord.objects.count())
        self._posttest()

    def test_hard_delete(self):
        self._pretest()
        tmo_tmp = TestModelOne.objects.create(extra_bool=True)
        tmo_tmp.delete()
        self.assertEquals(self.cs_count+1, ChangeSet.objects.count())
        self.assertEquals(self.rs_count+1, SoftDeleteRecord.objects.count())
        tmo_tmp.delete()
        self.assertEquals(self.cs_count, ChangeSet.objects.count())
        self.assertEquals(self.rs_count, SoftDeleteRecord.objects.count())
        self.assertRaises(TestModelOne.DoesNotExist,
                          TestModelOne.objects.get,
                          pk=tmo_tmp.pk)

    def test_soft_delete_policy(self):
        self.tmo_soft_delete.delete()
        self.tmo_delete_default.refresh_from_db()
        self.assertIsNone(self.tmo_delete_default.deleted_at)

    def test_soft_delete_cascade_policy(self):
        self.tmo_soft_delete_cascade.delete()
        self.tmo_soft_delete = TestModelSoftDelete.objects.all_with_deleted().filter(
            parent=self.tmo_soft_delete_cascade).first()
        self.assertIsNotNone(self.tmo_soft_delete.deleted_at)

    def test_soft_delete_policy_on_relation(self):
        self.tmo_soft_delete_relation_parent.delete()
        self.tmo_soft_delete_relation_child.refresh_from_db()
        self.assertIsNone(self.tmo_soft_delete_relation_child.deleted_at)

        self.tmo_soft_delete_relation_child_set_null.refresh_from_db()
        self.assertIsNone(self.tmo_soft_delete_relation_child_set_null.deleted_at)
        self.assertIsNone(self.tmo_soft_delete_relation_child_set_null.parent)

        self.tmo_soft_delete_relation_second_child = TestModelSoftDeleteOnRelationLevelSecondChild.objects.all_with_deleted().filter(
            parent=self.tmo_soft_delete_relation_parent).first()
        self.assertIsNotNone(self.tmo_soft_delete_relation_second_child.deleted_at)

    def test_soft_delete_one_to_one_not_softdele_object(self):
        self.tmo_soft_delete_relation_parent.delete()
        with self.assertRaises(TestModelOneToOneRelationWithNonSoftDeleteObject.DoesNotExist):
            self.tmo_non_soft_delete_one_to_one.refresh_from_db()

    def test_filter_delete(self):
        self._pretest()
        TestModelOne.objects.filter(pk=1).delete()
        self.assertEquals(self.cs_count+1, ChangeSet.objects.count())
        self.assertEquals(self.rs_count+56, SoftDeleteRecord.objects.count())
        self._posttest()

class AdminTest(BaseTest):
    def test_admin(self):
        client = Client()
        u = User.objects.create_user(username='test-user', password='test',
                                     email='test-user@example.com')
        u.is_staff = True
        u.is_superuser = True
        u.save()
        self.assertFalse(self.tmo1.deleted)
        client.login(username='test-user', password='test')
        url = '/admin/test_softdelete_app/testmodelone/1/'
        tmo = client.get(url)
        if tmo.status_code == 302:
            url = tmo['Location']
            tmo = client.get(url)
        self.assertEquals(tmo.status_code, 200)
        tmo = client.post(url, {'extra_bool': '1', 'deleted': '1'})
        self.assertEquals(tmo.status_code, 302)
        self.tmo1 = TestModelOne.objects.all_with_deleted().get(pk=self.tmo1.pk)
        self.assertTrue(self.tmo1.deleted)

class AuthorizationTest(BaseTest):
    def test_permission_needed(self):
        cl = Client()
        cl.login(username='NonSoftdeleteUser',
                 password='NonSoftdeletePassword')
        rv = cl.get(reverse('softdelete.changeset.list'))
        self.assertEquals(rv.status_code, 302)
        rv = cl.get(reverse('softdelete.changeset.view', args=(1,)))
        self.assertEquals(rv.status_code, 302)
        rv = cl.get(reverse('softdelete.changeset.undelete', args=(1,)))
        self.assertEquals(rv.status_code, 302)

class UndeleteTest(BaseTest):
    def pre_undelete(self, *args, **kwargs):
        self.pre_undelete_called = True

    def post_undelete(self, *args, **kwargs):
        self.post_undelete_called = True

    def test_undelete(self):
        self.pre_undelete_called = False
        self.post_undelete_called = False
        pre_undelete.connect(self.pre_undelete)
        post_undelete.connect(self.post_undelete)
        self.assertFalse(self.pre_undelete_called)
        self.assertFalse(self.post_undelete_called)
        self.cs_count = ChangeSet.objects.count()
        self.rs_count = SoftDeleteRecord.objects.count()
        self.tmo1.delete()
        self.assertEquals(self.cs_count+1, ChangeSet.objects.count())
        self.assertEquals(self.rs_count+56, SoftDeleteRecord.objects.count())
        self.tmo1 = TestModelOne.objects.all_with_deleted().get(pk=self.tmo1.pk)
        self.tmo2 = TestModelOne.objects.get(pk=self.tmo2.pk)
        self.assertTrue(self.tmo1.deleted)
        self.assertFalse(self.tmo2.deleted)
        self.tmo1.undelete()
        self.assertEquals(0, ChangeSet.objects.count())
        self.assertEquals(0, SoftDeleteRecord.objects.count())
        self.tmo1 = TestModelOne.objects.get(pk=self.tmo1.pk)
        self.tmo2 = TestModelOne.objects.get(pk=self.tmo2.pk)
        self.assertFalse(self.tmo1.deleted)
        self.assertFalse(self.tmo2.deleted)
        self.assertTrue(self.pre_undelete_called)
        self.assertTrue(self.post_undelete_called)

        self.tmo1.delete()
        self.assertEquals(self.cs_count+1, ChangeSet.objects.count())
        self.assertEquals(self.rs_count+56, SoftDeleteRecord.objects.count())
        self.tmo1 = TestModelOne.objects.all_with_deleted().get(pk=self.tmo1.pk)
        self.tmo2 = TestModelOne.objects.get(pk=self.tmo2.pk)
        self.assertTrue(self.tmo1.deleted)
        self.assertFalse(self.tmo2.deleted)
        TestModelOne.objects.deleted_set().undelete()
        self.assertEquals(0, ChangeSet.objects.count())
        self.assertEquals(0, SoftDeleteRecord.objects.count())
        self.tmo1 = TestModelOne.objects.get(pk=self.tmo1.pk)
        self.tmo2 = TestModelOne.objects.get(pk=self.tmo2.pk)
        self.assertFalse(self.tmo1.deleted)
        self.assertFalse(self.tmo2.deleted)
        self.assertTrue(self.pre_undelete_called)
        self.assertTrue(self.post_undelete_called)

class M2MTests(BaseTest):
    def test_m2mdelete(self):
        t3 = TestModelThree.objects.all()[0]
        self.assertFalse(t3.deleted)
        for x in t3.tmos.all():
            self.assertFalse(x.deleted)
        t3.delete()
        for x in t3.tmos.all():
            self.assertFalse(x.deleted)


class SoftDeleteRelatedFieldLookupsTests(BaseTest):
    def test_related_foreign_key(self):
        tmt1 = TestModelTwo.objects.create(extra_int=100, tmo=self.tmo1)
        tmt2 = TestModelTwo.objects.create(extra_int=100, tmo=self.tmo2)

        self.assertEquals(self.tmo1.tmts.filter(extra_int=100).count(), 1)
        self.assertEquals(self.tmo1.tmts.filter(extra_int=100)[0].pk, tmt1.pk)
        self.assertEquals(self.tmo2.tmts.filter(extra_int=100).count(), 1)
        self.assertEquals(self.tmo2.tmts.filter(extra_int=100)[0].pk, tmt2.pk)

        self.assertEquals(self.tmo1.tmts.get(extra_int=100), tmt1)
        self.assertEquals(self.tmo2.tmts.get(extra_int=100), tmt2)

        tmt1.delete()
        self.assertEquals(self.tmo1.tmts.filter(extra_int=100).count(), 0)
        tmt1.undelete()
        self.assertEquals(self.tmo1.tmts.filter(extra_int=100).count(), 1)

        tmt1.delete()
        tmt1.delete()
        self.assertRaises(TestModelTwo.DoesNotExist,
                          self.tmo1.tmts.get, extra_int=100)

    def test_related_m2m(self):
        t31 = TestModelThree.objects.create(extra_int=100)
        TestModelThrough.objects.create(tmo1=self.tmo1, tmo3=t31)
        t32 = TestModelThree.objects.create(extra_int=100)
        TestModelThrough.objects.create(tmo1=self.tmo2, tmo3=t32)

        self.assertEquals(self.tmo1.testmodelthree_set.filter(extra_int=100).count(), 1)
        self.assertEquals(self.tmo1.testmodelthree_set.filter(extra_int=100)[0].pk, t31.pk)
        self.assertEquals(self.tmo2.testmodelthree_set.filter(extra_int=100).count(), 1)
        self.assertEquals(self.tmo2.testmodelthree_set.filter(extra_int=100)[0].pk, t32.pk)

        self.assertEquals(self.tmo1.testmodelthree_set.get(extra_int=100), t31)
        self.assertEquals(self.tmo2.testmodelthree_set.get(extra_int=100), t32)

        t31.delete()
        self.assertEquals(self.tmo1.testmodelthree_set.filter(extra_int=100).count(), 0)
        t31.undelete()
        self.assertEquals(self.tmo1.testmodelthree_set.filter(extra_int=100).count(), 1)

        t31.delete()
        t31.delete()
        self.assertRaises(TestModelThree.DoesNotExist,
                          self.tmo1.testmodelthree_set.get, extra_int=100)
