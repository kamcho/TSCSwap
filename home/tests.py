from django.test import TestCase
from users.models import MyUser, PersonalProfile
from home.models import Level, Schools, Counties, Constituencies, Wards, SwapPreference, Subject, MySubject, Curriculum
from home.matching import find_matches

class MatchingLogicTests(TestCase):
    def setUp(self):
        # Setup basic data
        self.curriculum = Curriculum.objects.create(name="CBC", description="Competency Based Curriculum")
        
        # Leves
        self.primary_level = Level.objects.create(name="Primary", code="PRI", curriculum=self.curriculum)
        self.secondary_level = Level.objects.create(name="Secondary", code="SEC", curriculum=self.curriculum)
        
        # Locations
        self.county_nairobi = Counties.objects.create(name="Nairobi")
        self.county_mombasa = Counties.objects.create(name="Mombasa")
        self.county_kisumu = Counties.objects.create(name="Kisumu")
        self.county_nakuru = Counties.objects.create(name="Nakuru")
        
        self.const_nairobi = Constituencies.objects.create(name="Westlands", county=self.county_nairobi)
        self.const_mombasa = Constituencies.objects.create(name="Nyali", county=self.county_mombasa)
        self.const_kisumu = Constituencies.objects.create(name="Kisumu Central", county=self.county_kisumu)
        self.const_nakuru = Constituencies.objects.create(name="Nakuru West", county=self.county_nakuru)
        
        self.ward_nairobi = Wards.objects.create(name="Westlands", constituency=self.const_nairobi)
        self.ward_mombasa = Wards.objects.create(name="Nyali", constituency=self.const_mombasa)
        self.ward_kisumu = Wards.objects.create(name="Kisumu Central", constituency=self.const_kisumu)
        self.ward_nakuru = Wards.objects.create(name="Nakuru West", constituency=self.const_nakuru)
        
        # Schools
        self.school_nairobi = Schools.objects.create(name="Nairobi Pri", gender="Mixed", level=self.primary_level, boarding="Day", curriculum=self.curriculum, postal_code="00100", ward=self.ward_nairobi)
        self.school_mombasa = Schools.objects.create(name="Mombasa Pri", gender="Mixed", level=self.primary_level, boarding="Day", curriculum=self.curriculum, postal_code="80100", ward=self.ward_mombasa)
        
        self.school_kisumu_sec = Schools.objects.create(name="Kisumu High", gender="Mixed", level=self.secondary_level, boarding="Boarding", curriculum=self.curriculum, postal_code="40100", ward=self.ward_kisumu)
        self.school_nakuru_sec = Schools.objects.create(name="Nakuru High", gender="Mixed", level=self.secondary_level, boarding="Boarding", curriculum=self.curriculum, postal_code="20100", ward=self.ward_nakuru)
        
        # Subjects
        self.math = Subject.objects.create(name="Mathematics", level=self.secondary_level)
        self.chem = Subject.objects.create(name="Chemistry", level=self.secondary_level)
        self.eng = Subject.objects.create(name="English", level=self.secondary_level)

    def create_teacher(self, email, level, school, desired_county=None, open_to_all_counties=[]):
        user = MyUser.objects.create_user(email=email, password='password')
        profile = PersonalProfile.objects.create(user=user, level=level, school=school)
        
        pref = SwapPreference.objects.create(user=user, desired_county=desired_county)
        if open_to_all_counties:
            pref.open_to_all.set(open_to_all_counties)
            
        return user

    def test_primary_match_success(self):
        """
        Teacher A (Nairobi) wants Mombasa.
        Teacher B (Mombasa) wants Nairobi.
        Should MATCH.
        """
        teacher_a = self.create_teacher('a@test.com', self.primary_level, self.school_nairobi, desired_county=self.county_mombasa)
        teacher_b = self.create_teacher('b@test.com', self.primary_level, self.school_mombasa, desired_county=self.county_nairobi)
        
        matches_a = find_matches(teacher_a)
        self.assertIn(teacher_b, matches_a)
        
        matches_b = find_matches(teacher_b)
        self.assertIn(teacher_a, matches_b)

    def test_primary_match_fail_one_way(self):
        """
        Teacher A (Nairobi) wants Mombasa.
        Teacher B (Mombasa) wants Kisumu (NOT Nairobi).
        
        A wants matching with B (based on location), BUT B does not want A's location.
        Should NOT match.
        """
        teacher_a = self.create_teacher('a@test.com', self.primary_level, self.school_nairobi, desired_county=self.county_mombasa)
        teacher_b = self.create_teacher('b@test.com', self.primary_level, self.school_mombasa, desired_county=self.county_kisumu) # Wants Kisumu
        
        matches_a = find_matches(teacher_a)
        self.assertNotIn(teacher_b, matches_a)

    def test_secondary_match_success_exact_subjects(self):
        """
        Teacher C (Kisumu) -> Wants Nakuru. Subs: Math, Chem.
        Teacher D (Nakuru) -> Wants Kisumu. Subs: Math, Chem.
        Should MATCH.
        """
        teacher_c = self.create_teacher('c@test.com', self.secondary_level, self.school_kisumu_sec, desired_county=self.county_nakuru)
        mysub_c = MySubject.objects.create(user=teacher_c)
        mysub_c.subject.set([self.math, self.chem])
        
        teacher_d = self.create_teacher('d@test.com', self.secondary_level, self.school_nakuru_sec, desired_county=self.county_kisumu)
        mysub_d = MySubject.objects.create(user=teacher_d)
        mysub_d.subject.set([self.math, self.chem])
        
        matches_c = find_matches(teacher_c)
        self.assertIn(teacher_d, matches_c)

    def test_secondary_match_fail_different_subjects(self):
        """
        Teacher C (Kisumu) -> Wants Nakuru. Subs: Math, Chem.
        Teacher E (Nakuru) -> Wants Kisumu. Subs: English.
        Should NOT match.
        """
        teacher_c = self.create_teacher('c@test.com', self.secondary_level, self.school_kisumu_sec, desired_county=self.county_nakuru)
        mysub_c = MySubject.objects.create(user=teacher_c)
        mysub_c.subject.set([self.math, self.chem])
        
        teacher_e = self.create_teacher('e@test.com', self.secondary_level, self.school_nakuru_sec, desired_county=self.county_kisumu)
        mysub_e = MySubject.objects.create(user=teacher_e)
        mysub_e.subject.set([self.eng]) # Different subject
        
        matches_c = find_matches(teacher_c)
        self.assertNotIn(teacher_e, matches_c)

    def test_secondary_match_fail_subset_subjects(self):
        """
        Teacher C (Kisumu) -> Wants Nakuru. Subs: Math, Chem.
        Teacher F (Nakuru) -> Wants Kisumu. Subs: Math. (Missing Chem).
        Should NOT match (assuming exact match required).
        """
        teacher_c = self.create_teacher('c@test.com', self.secondary_level, self.school_kisumu_sec, desired_county=self.county_nakuru)
        mysub_c = MySubject.objects.create(user=teacher_c)
        mysub_c.subject.set([self.math, self.chem])
        
        teacher_f = self.create_teacher('f@test.com', self.secondary_level, self.school_nakuru_sec, desired_county=self.county_kisumu)
        mysub_f = MySubject.objects.create(user=teacher_f)
        mysub_f.subject.set([self.math]) # Only Math
        
        matches_c = find_matches(teacher_c)
        self.assertNotIn(teacher_f, matches_c)

    def test_open_to_all_logic(self):
        """
        Teacher A (Nairobi) -> Wants Matching with [Open To All: Mombasa].
        Teacher B (Mombasa) -> Wants Matching with [Open To All: Nairobi].
        Should Match.
        """
        teacher_a = self.create_teacher('a_open@test.com', self.primary_level, self.school_nairobi, open_to_all_counties=[self.county_mombasa])
        teacher_b = self.create_teacher('b_open@test.com', self.primary_level, self.school_mombasa, open_to_all_counties=[self.county_nairobi])
        
        matches_a = find_matches(teacher_a)
        self.assertIn(teacher_b, matches_a)

    def test_triangle_swap_secondary_strict_subjects(self):
        """
        Triangle Swap:
        A (Kisumu) -> Wants Nakuru. Subs: Math, Chem.
        B (Nakuru) -> Wants Mombasa. Subs: Math, Chem.
        C (Mombasa) -> Wants Kisumu. Subs: Math, Chem.
        
        Should MATCH (Loop + Same Subjects).
        """
        from home.triangle_swap_utils import find_triangle_swaps_secondary
        
        # Teacher A
        teacher_a = self.create_teacher('a_tri@test.com', self.secondary_level, self.school_kisumu_sec, desired_county=self.county_nakuru)
        mysub_a = MySubject.objects.create(user=teacher_a)
        mysub_a.subject.set([self.math, self.chem])
        
        # Teacher B
        teacher_b = self.create_teacher('b_tri@test.com', self.secondary_level, self.school_nakuru_sec, desired_county=self.county_mombasa)
        mysub_b = MySubject.objects.create(user=teacher_b)
        mysub_b.subject.set([self.math, self.chem])
        
        # Teacher C (Mombasa Secondary)
        school_mombasa_sec = Schools.objects.create(name="Mombasa High", gender="Mixed", level=self.secondary_level, boarding="Boarding", curriculum=self.curriculum, postal_code="80100", ward=self.ward_mombasa)
        teacher_c = self.create_teacher('c_tri@test.com', self.secondary_level, school_mombasa_sec, desired_county=self.county_kisumu)
        mysub_c = MySubject.objects.create(user=teacher_c)
        mysub_c.subject.set([self.math, self.chem])
        
        # Find triangles
        qs = MyUser.objects.filter(id__in=[teacher_a.id, teacher_b.id, teacher_c.id])
        triangles = find_triangle_swaps_secondary(qs)
        
        # Should find at least one triangle
        self.assertTrue(len(triangles) > 0)
        
        # Verify participants
        found_ids = [t.id for t in triangles[0]]
        self.assertIn(teacher_a.id, found_ids)
        self.assertIn(teacher_b.id, found_ids)
        self.assertIn(teacher_c.id, found_ids)

    def test_triangle_swap_secondary_fail_partial_subjects(self):
        """
        Triangle Swap FAIL:
        A: Math, Chem
        B: Math, English (Different)
        C: Math, Chem
        
        Should NOT match.
        """
        from home.triangle_swap_utils import find_triangle_swaps_secondary
        
        # Teacher A
        teacher_a = self.create_teacher('a_tri_fail@test.com', self.secondary_level, self.school_kisumu_sec, desired_county=self.county_nakuru)
        mysub_a = MySubject.objects.create(user=teacher_a)
        mysub_a.subject.set([self.math, self.chem])
        
        # Teacher B (Different Subs)
        teacher_b = self.create_teacher('b_tri_fail@test.com', self.secondary_level, self.school_nakuru_sec, desired_county=self.county_mombasa)
        mysub_b = MySubject.objects.create(user=teacher_b)
        mysub_b.subject.set([self.math, self.eng]) # Partial match (Math) but not exact
        
        # Teacher C
        school_mombasa_sec = Schools.objects.create(name="Mombasa High 2", gender="Mixed", level=self.secondary_level, boarding="Boarding", curriculum=self.curriculum, postal_code="80100", ward=self.ward_mombasa)
        teacher_c = self.create_teacher('c_tri_fail@test.com', self.secondary_level, school_mombasa_sec, desired_county=self.county_kisumu)
        mysub_c = MySubject.objects.create(user=teacher_c)
        mysub_c.subject.set([self.math, self.chem])
        
        # Find triangles
        qs = MyUser.objects.filter(id__in=[teacher_a.id, teacher_b.id, teacher_c.id])
        triangles = find_triangle_swaps_secondary(qs)
        
        # Should find NO triangles
        self.assertEqual(len(triangles), 0)
