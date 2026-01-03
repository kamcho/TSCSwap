from django.db.models import Q
from users.models import MyUser
from home.models import FastSwap, MySubject

def get_fast_swap_current_county(fs):
    return fs.current_county

def get_user_current_county(user):
    if hasattr(user, 'profile') and user.profile and user.profile.school and user.profile.school.ward:
        try:
            return user.profile.school.ward.constituency.county
        except:
            return None
    return None

def fs_wants_county(fs, county):
    if not county:
        return False
    if fs.most_preferred and fs.most_preferred.id == county.id:
        return True
    if fs.acceptable_county.filter(id=county.id).exists():
        return True
    return False

def user_wants_county(user, county):
    if not county or not hasattr(user, 'swappreference'):
        return False
    pref = user.swappreference
    if pref.desired_county and pref.desired_county.id == county.id:
        return True
    if pref.open_to_all.filter(id=county.id).exists():
        return True
    return False

def get_fs_subjects(fs):
    return set(fs.subjects.values_list('id', flat=True))

def get_user_subjects(user):
    return set(MySubject.objects.filter(user=user).values_list('subject__id', flat=True))

def find_mutual_matches_for_fast_swap(fs):
    """
    Finds mutual matches for a FastSwap instance.
    Returns:
        {
            'fast_swaps': list of matching FastSwap objects,
            'users': list of matching MyUser objects
        }
    """
    fs_level = fs.level
    fs_county = fs.current_county
    is_secondary = 'secondary' in fs_level.name.lower() or 'high' in fs_level.name.lower()
    fs_subjects = get_fs_subjects(fs) if is_secondary else set()

    # 1. Match with other FastSwaps
    # They want MY county AND I want THEIR county
    # Filter by level and active (FastSwap doesn't have active field, assume all are active)
    fs_target_counties = [fs.most_preferred.id] if fs.most_preferred else []
    fs_target_counties.extend(list(fs.acceptable_county.values_list('id', flat=True)))
    
    if not fs_target_counties:
        matching_fs = FastSwap.objects.none()
    else:
        # Conditions for other FastSwap (ofs):
        # 1. ofs level matches fs level
        # 2. ofs current_county in fs_target_counties
        # 3. ofs wants fs_county
        matching_fs = FastSwap.objects.filter(
            ~Q(id=fs.id),
            level=fs_level,
            current_county__id__in=fs_target_counties
        ).filter(
            Q(most_preferred=fs_county) | Q(acceptable_county=fs_county)
        ).distinct()

        if is_secondary:
            valid_ids = []
            for ofs in matching_fs:
                if get_fs_subjects(ofs) == fs_subjects:
                    valid_ids.append(ofs.id)
            matching_fs = matching_fs.filter(id__in=valid_ids)

    # 2. Match with MyUsers
    matching_users = MyUser.objects.filter(
        is_active=True,
        profile__level=fs_level,
        profile__school__ward__constituency__county__id__in=fs_target_counties
    ).filter(
        Q(swappreference__desired_county=fs_county) | Q(swappreference__open_to_all=fs_county)
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county'
    ).distinct()

    if is_secondary:
        valid_user_ids = []
        if not fs_subjects: #fs has no subjects
             matching_users = MyUser.objects.none()
        else:
            for user in matching_users:
                if get_user_subjects(user) == fs_subjects:
                    valid_user_ids.append(user.id)
            matching_users = matching_users.filter(id__in=valid_user_ids)

    return {
        'fast_swaps': list(matching_fs),
        'users': list(matching_users)
    }

def find_triangle_matches_for_fast_swap(fs):
    """
    Finds triangle matches for a FastSwap instance (A -> B -> C -> A).
    Entity A = fs.
    Entity B, C can be FastSwap or MyUser.
    """
    fs_level = fs.level
    fs_county = fs.current_county
    if not fs_county or not fs_level:
        return []
        
    is_secondary = 'secondary' in fs_level.name.lower() or 'high' in fs_level.name.lower()
    fs_subjects = get_fs_subjects(fs) if is_secondary else set()

    # Get all potential participants (same level, different id/entity)
    # Users
    potential_users = MyUser.objects.filter(
        is_active=True,
        profile__level=fs_level,
        profile__school__ward__constituency__county__isnull=False,
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county'
    ).prefetch_related('swappreference__open_to_all')

    # FastSwaps
    potential_fs = FastSwap.objects.filter(
        level=fs_level,
        current_county__isnull=False
    ).exclude(id=fs.id).prefetch_related('acceptable_county', 'subjects')

    # Step 1: Find all B that A (fs) wants
    # fs targets
    fs_targets = set([fs.most_preferred.id] if fs.most_preferred else [])
    fs_targets.update(fs.acceptable_county.values_list('id', flat=True))

    entities_b = [] # List of (type, object, current_county_id, target_county_ids)
    
    # Check users for B
    for u in potential_users:
        u_county = get_user_current_county(u)
        if u_county and u_county.id in fs_targets:
            if not is_secondary or get_user_subjects(u) == fs_subjects:
                targets = set([u.swappreference.desired_county.id] if u.swappreference.desired_county else [])
                targets.update(u.swappreference.open_to_all.values_list('id', flat=True))
                entities_b.append(('user', u, u_county.id, targets))
    
    # Check other FastSwaps for B
    for ofs in potential_fs:
        ofs_county = ofs.current_county
        if ofs_county and ofs_county.id in fs_targets:
            if not is_secondary or get_fs_subjects(ofs) == fs_subjects:
                targets = set([ofs.most_preferred.id] if ofs.most_preferred else [])
                targets.update(ofs.acceptable_county.values_list('id', flat=True))
                entities_b.append(('fastswap', ofs, ofs_county.id, targets))

    triangles = []
    processed_triplets = set()

    # Step 2: For each B, find C
    for type_b, obj_b, county_b_id, targets_b in entities_b:
        # Step 3: Find all C that B wants
        # C can be from potential_users or potential_fs
        for u_c in potential_users:
            if u_c.id == obj_b.id and type_b == 'user': continue
            u_c_county = get_user_current_county(u_c)
            if u_c_county and u_c_county.id in targets_b:
                if not is_secondary or get_user_subjects(u_c) == fs_subjects:
                    # Does C want A?
                    if user_wants_county(u_c, fs_county):
                        # Found A -> B -> C -> A
                        triplet = tuple(sorted([f"fs_{fs.id}", f"{type_b}_{obj_b.id}", f"user_{u_c.id}"]))
                        if triplet not in processed_triplets:
                            processed_triplets.add(triplet)
                            triangles.append({
                                'entity_b': {'type': type_b, 'obj': obj_b},
                                'entity_c': {'type': 'user', 'obj': u_c}
                            })
                            
        for fs_c in potential_fs:
            if fs_c.id == obj_b.id and type_b == 'fastswap': continue
            fs_c_county = fs_c.current_county
            if fs_c_county and fs_c_county.id in targets_b:
                if not is_secondary or get_fs_subjects(fs_c) == fs_subjects:
                    # Does C want A?
                    if fs_wants_county(fs_c, fs_county):
                        # Found A -> B -> C -> A
                        triplet = tuple(sorted([f"fs_{fs.id}", f"{type_b}_{obj_b.id}", f"fs_{fs_c.id}"]))
                        if triplet not in processed_triplets:
                            processed_triplets.add(triplet)
                            triangles.append({
                                'entity_b': {'type': type_b, 'obj': obj_b},
                                'entity_c': {'type': 'fastswap', 'obj': fs_c}
                            })

    return triangles
