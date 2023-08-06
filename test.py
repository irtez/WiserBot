


def get_userids_with_params(tarifs: list, classes: list | str, isAll: bool = False):

    result_dict = {}
    text = "SELECT user_id FROM users WHERE "
    i = 0
    for tarif in tarifs:
        if tarif == '3':
            text += "free_period_status = 'using' OR "
        else:
            i += 1
            text += f"tarif = :tarif{i} OR "
            result_dict[f'tarif{i}'] = tarif
        
    text = text[:-3]
    if not classes == 'ALL':
        text += "AND "
        i = 0
        for class_id in classes:
            i += 1
            text += f"class_id = :class_id{i} OR "
            result_dict[f'class_id{i}'] = class_id
        text = text[:-3]
    text += "AND access = 1"
    print(text)

get_userids_with_params(['3'], [1])